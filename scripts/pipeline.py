"""
Extraction Pipeline (HR Resume Version)

简历提取后处理管道，串联所有后处理算法：
1. Source Grounding - 文本对齐到源文件位置
2. Overlap Deduplication - 重叠去重
3. Confidence Scoring - 置信度评分
4. Entity Resolution - 实体消歧 (默认开启: 合并同名候选人)
5. Relation Inference - 关系推断 (默认开启: 人-公司-技能关系)
6. Knowledge Graph Injection - KG 格式转换

CLI 入口：
    python pipeline.py --input raw.json --source resume.txt --output result.json
"""

import json
import sys
import argparse
from pathlib import Path

# 导入所有处理模块
from source_grounding import SourceGrounder
from overlap_dedup import OverlapDeduplicator
from confidence_scorer import ConfidenceScorer
from entity_resolver import EntityResolver
from relation_inferrer import RelationInferrer
from kg_injector import KGInjector


class ExtractionPipeline:
    """提取后处理管道"""

    # 默认配置
    DEFAULT_CONFIG = {
        "source_grounding": True,
        "overlap_dedup": True,
        "confidence_scoring": True,
        "entity_resolution": True,   # HR 场景默认开启，合并同名候选人
        "relation_inference": True,   # HR 场景默认开启，推断人-公司-技能关系
        "kg_injection": False,        # 默认关闭，输出原始格式
        "confidence_threshold": 0.3,
        "overlap_threshold": 0.5,
        "entity_similarity_threshold": 0.7,
        "scope_window": 50,
        "type_aware_dedup": False,
    }

    def __init__(self, source_text: str, config: dict = None, source_file: str = None):
        """
        Args:
            source_text: 原始源文件文本
            config: 配置字典（可选）
            source_file: 源文件名（可选，用于 KG 输出的 Source 标注）
        """
        self.source_text = source_text
        self.source_file = source_file
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}

        # 初始化各模块
        self.grounder = SourceGrounder(source_text)
        self.deduplicator = OverlapDeduplicator(
            overlap_threshold=self.config["overlap_threshold"],
            type_aware=self.config["type_aware_dedup"],
        )
        self.scorer = ConfidenceScorer()
        self.resolver = EntityResolver(
            threshold=self.config["entity_similarity_threshold"]
        )
        self.inferrer = RelationInferrer(
            scope_window=self.config["scope_window"]
        )
        self.injector = KGInjector(
            confidence_threshold=self.config["confidence_threshold"]
        )

    def process(self, raw_extractions: list[dict]) -> dict:
        """
        执行完整的后处理管道

        Args:
            raw_extractions: LLM 提取的原始列表

        Returns:
            {
                "extractions": [...],
                "relations": [...],
                "kg_format": {...},
                "stats": {...}
            }
        """
        extractions = raw_extractions
        inferred_relations = []

        print(f"\n=== Pipeline 开始 ===")
        print(f"原始提取项: {len(extractions)} 个\n")

        # 1. Source Grounding
        if self.config["source_grounding"]:
            print("[1/6] Source Grounding...")
            extractions = self.grounder.process(extractions)
            matched = sum(1 for e in extractions
                          if e.get('source_location', {}).get('match_type') in ['exact', 'normalized', 'fuzzy'])
            print(f"  [OK] {matched}/{len(extractions)} matched\n")

        # 注入 source_file (供 KG 输出使用)
        if self.source_file:
            for ext in extractions:
                if 'source_file' not in ext:
                    ext['source_file'] = self.source_file

        # 2. Overlap Deduplication
        if self.config["overlap_dedup"]:
            print("[2/6] Overlap Deduplication...")
            before_count = len(extractions)
            extractions = self.deduplicator.process(extractions)
            removed = before_count - len(extractions)
            print(f"  [OK] removed {removed}, remaining {len(extractions)}\n")

        # 3. Confidence Scoring
        if self.config["confidence_scoring"]:
            print("[3/6] Confidence Scoring...")
            extractions = self.scorer.process(extractions)
            avg_conf = sum(e.get('confidence', 0) for e in extractions) / len(extractions) if extractions else 0
            print(f"  [OK] avg confidence: {avg_conf:.3f}\n")

        # 4. Entity Resolution
        if self.config["entity_resolution"]:
            print("[4/6] Entity Resolution...")
            before_entities = sum(1 for e in extractions if e.get('type') == 'entity')
            extractions = self.resolver.process(extractions)
            after_entities = sum(1 for e in extractions if e.get('type') == 'entity')
            merged = before_entities - after_entities
            print(f"  [OK] merged {merged} similar entities\n")
        else:
            print("[4/6] Entity Resolution (skipped)\n")

        # 5. Relation Inference
        if self.config["relation_inference"]:
            print("[5/6] Relation Inference...")
            extractions, inferred_relations = self.inferrer.process(extractions)
            print(f"  [OK] inferred {len(inferred_relations)} relations\n")
        else:
            print("[5/6] Relation Inference (skipped)\n")

        # 6. KG Injection
        kg_format = None
        if self.config["kg_injection"]:
            print("[6/6] Knowledge Graph Injection...")
            kg_format = self.injector.convert(extractions, inferred_relations)
            print(f"  [OK] converted to KG format: {len(kg_format['entities'])} entities, {len(kg_format['relations'])} relations\n")
        else:
            print("[6/6] Knowledge Graph Injection (跳过)\n")

        # 统计
        stats = self._compute_stats(extractions, inferred_relations)

        print("=== Pipeline 完成 ===\n")

        return {
            "extractions": extractions,
            "inferred_relations": inferred_relations,
            "kg_format": kg_format,
            "stats": stats,
        }

    def _compute_stats(self, extractions: list[dict], relations: list[dict]) -> dict:
        """
        计算统计信息

        Args:
            extractions: 提取列表
            relations: 关系列表

        Returns:
            统计字典
        """
        # 总数
        total = len(extractions)

        # 按类型统计
        by_type = {}
        for ext in extractions:
            ext_type = ext.get('type', 'unknown')
            by_type[ext_type] = by_type.get(ext_type, 0) + 1

        # 平均置信度
        confidences = [e.get('confidence', 0) for e in extractions]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        # 置信度分布
        high_conf = sum(1 for c in confidences if c >= 0.7)
        medium_conf = sum(1 for c in confidences if 0.3 <= c < 0.7)
        low_conf = sum(1 for c in confidences if c < 0.3)

        # 匹配质量统计
        match_types = {}
        for ext in extractions:
            match_type = ext.get('source_location', {}).get('match_type', 'none')
            match_types[match_type] = match_types.get(match_type, 0) + 1

        return {
            "total_extractions": total,
            "by_type": by_type,
            "avg_confidence": round(avg_confidence, 3),
            "confidence_distribution": {
                "high (>=0.7)": high_conf,
                "medium (0.3-0.7)": medium_conf,
                "low (<0.3)": low_conf,
            },
            "match_quality": match_types,
            "inferred_relations": len(relations),
        }


def main():
    """CLI 入口"""
    parser = argparse.ArgumentParser(
        description="Extraction Pipeline - 后处理 LLM 提取结果"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="输入 JSON 文件路径 (LLM 提取的原始结果)"
    )
    parser.add_argument(
        "--source",
        required=True,
        help="源文件路径 (用于 Source Grounding)"
    )
    parser.add_argument(
        "--config",
        help="配置 JSON 文件路径 (可选)"
    )
    parser.add_argument(
        "--output",
        help="输出 JSON 文件路径 (可选，默认打印到stdout)"
    )
    parser.add_argument(
        "--enable-entity-resolution",
        action="store_true",
        help="启用实体消歧"
    )
    parser.add_argument(
        "--enable-relation-inference",
        action="store_true",
        help="启用关系推断"
    )
    parser.add_argument(
        "--enable-kg-injection",
        action="store_true",
        help="启用 KG 格式转换"
    )

    args = parser.parse_args()

    # 读取输入
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误: 输入文件不存在: {args.input}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, 'r', encoding='utf-8') as f:
        raw_extractions = json.load(f)

    # 兼容两种输入格式: 纯数组 [...] 或 {"extractions": [...]}
    if isinstance(raw_extractions, dict) and "extractions" in raw_extractions:
        raw_extractions = raw_extractions["extractions"]

    if not isinstance(raw_extractions, list):
        print(f"错误: 输入JSON必须是数组或包含'extractions'键的对象", file=sys.stderr)
        sys.exit(1)

    # 读取源文件
    source_path = Path(args.source)
    if not source_path.exists():
        print(f"错误: 源文件不存在: {args.source}", file=sys.stderr)
        sys.exit(1)

    with open(source_path, 'r', encoding='utf-8') as f:
        source_text = f.read()

    # 读取配置 (支持预设格式和直接配置格式)
    config = {}
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                raw_config = json.load(f)
            # 预设格式: {"pipeline_config": {...}} → 提取嵌套配置
            if "pipeline_config" in raw_config:
                config = raw_config["pipeline_config"]
            else:
                config = raw_config

    # 命令行开关覆盖配置
    if args.enable_entity_resolution:
        config["entity_resolution"] = True
    if args.enable_relation_inference:
        config["relation_inference"] = True
    if args.enable_kg_injection:
        config["kg_injection"] = True

    # 执行管道
    pipeline = ExtractionPipeline(source_text, config, source_file=source_path.name)
    result = pipeline.process(raw_extractions)

    # 输出结果
    output_data = {
        "extractions": result["extractions"],
        "inferred_relations": result["inferred_relations"],
        "stats": result["stats"],
    }

    if result["kg_format"]:
        output_data["kg_format"] = result["kg_format"]

    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"[OK] Result saved to: {output_path}")
    else:
        print(json.dumps(output_data, indent=2, ensure_ascii=False))

    # 打印统计
    print("\n=== 统计信息 ===")
    print(json.dumps(result["stats"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
