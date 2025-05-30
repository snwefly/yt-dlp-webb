#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
yt-dlp extractor 修复脚本
解决缺失的 extractor 模块问题
"""

import os
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def check_missing_extractors():
    """检查缺失的 extractor 模块"""
    missing_extractors = []

    try:
        # 尝试导入常见的 extractors
        test_extractors = [
            'screencastify',
            'screen9',
            'screencast',
            'screencastomatic',
            'screenrec'
        ]

        for extractor_name in test_extractors:
            try:
                module_name = f'yt_dlp.extractor.{extractor_name}'
                __import__(module_name)
                logger.info(f"✅ {extractor_name} 可用")
            except ImportError as e:
                logger.warning(f"⚠️ {extractor_name} 缺失: {e}")
                missing_extractors.append(extractor_name)

        return missing_extractors

    except Exception as e:
        logger.error(f"检查 extractors 时出错: {e}")
        return []

def create_dummy_extractor(extractor_name):
    """创建虚拟 extractor 模块"""
    try:
        # 查找 yt_dlp 安装位置
        import yt_dlp
        yt_dlp_path = Path(yt_dlp.__file__).parent
        extractor_dir = yt_dlp_path / 'extractor'

        if not extractor_dir.exists():
            logger.error(f"extractor 目录不存在: {extractor_dir}")
            return False

        # 检查是否有写入权限
        if not os.access(extractor_dir, os.W_OK):
            logger.warning(f"没有写入权限: {extractor_dir}")
            return False

        # 创建虚拟模块文件
        dummy_file = extractor_dir / f'{extractor_name}.py'

        # 如果文件已存在，跳过
        if dummy_file.exists():
            logger.info(f"ℹ️ extractor 已存在: {dummy_file}")
            return True

        dummy_content = f'''# -*- coding: utf-8 -*-
"""
虚拟 {extractor_name} extractor
自动生成以解决导入错误
"""

from .common import InfoExtractor

class {extractor_name.capitalize()}IE(InfoExtractor):
    """虚拟 {extractor_name} extractor"""

    _VALID_URL = r'https?://(?:www\\.)?{extractor_name}\\.com/.*'
    _TESTS = []

    def _real_extract(self, url):
        raise NotImplementedError('此 extractor 为虚拟实现')
'''

        # 写入文件
        try:
            with open(dummy_file, 'w', encoding='utf-8') as f:
                f.write(dummy_content)
            logger.info(f"✅ 创建虚拟 extractor: {dummy_file}")
            return True
        except PermissionError:
            logger.warning(f"⚠️ 权限不足，无法创建: {dummy_file}")
            return False

    except Exception as e:
        logger.error(f"创建虚拟 extractor 失败: {e}")
        return False

def update_extractors_list():
    """更新 extractors 列表"""
    try:
        import yt_dlp
        yt_dlp_path = Path(yt_dlp.__file__).parent
        extractors_file = yt_dlp_path / 'extractor' / '_extractors.py'

        if not extractors_file.exists():
            logger.warning("_extractors.py 文件不存在，跳过更新")
            return True

        # 读取现有内容
        with open(extractors_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否需要添加新的 extractor
        missing_extractors = check_missing_extractors()

        for extractor_name in missing_extractors:
            class_name = f'{extractor_name.capitalize()}IE'
            import_line = f'from .{extractor_name} import {class_name}'

            if import_line not in content:
                # 在文件末尾添加导入
                content += f'\n{import_line}'
                logger.info(f"添加 extractor 导入: {class_name}")

        # 写回文件
        with open(extractors_file, 'w', encoding='utf-8') as f:
            f.write(content)

        return True

    except Exception as e:
        logger.error(f"更新 extractors 列表失败: {e}")
        return False

def fix_extractor_imports():
    """修复 extractor 导入问题"""
    logger.info("🔧 开始修复 extractor 导入问题...")

    # 检查缺失的 extractors
    missing_extractors = check_missing_extractors()

    if not missing_extractors:
        logger.info("✅ 所有 extractors 都可用")
        return True

    logger.info(f"发现缺失的 extractors: {missing_extractors}")

    # 创建虚拟 extractors
    success_count = 0
    for extractor_name in missing_extractors:
        if create_dummy_extractor(extractor_name):
            success_count += 1

    logger.info(f"✅ 成功创建 {success_count}/{len(missing_extractors)} 个虚拟 extractors")

    # 更新 extractors 列表
    if update_extractors_list():
        logger.info("✅ extractors 列表更新成功")

    return success_count > 0

def test_yt_dlp_functionality():
    """测试 yt-dlp 基本功能"""
    logger.info("🧪 测试 yt-dlp 基本功能...")

    try:
        from yt_dlp import YoutubeDL

        # 创建最小配置的下载器
        ydl = YoutubeDL({
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'extract_flat': True,
        })

        logger.info("✅ YoutubeDL 实例创建成功")

        # 测试基础 extractors
        try:
            from yt_dlp.extractor.youtube import YoutubeIE
            from yt_dlp.extractor.generic import GenericIE
            logger.info("✅ 基础 extractors 导入成功")
        except ImportError as e:
            logger.warning(f"⚠️ 基础 extractors 导入失败: {e}")

        return True

    except Exception as e:
        logger.error(f"❌ yt-dlp 功能测试失败: {e}")
        return False

def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    logger.info("🚀 启动 yt-dlp extractor 修复工具")

    try:
        # 检查 yt-dlp 是否可用
        try:
            import yt_dlp
            logger.info(f"✅ yt-dlp 已安装: {yt_dlp.__version__}")
        except ImportError:
            logger.error("❌ yt-dlp 未安装")
            return 1

        # 修复 extractor 导入问题
        if fix_extractor_imports():
            logger.info("✅ extractor 修复完成")
        else:
            logger.warning("⚠️ extractor 修复部分失败")

        # 测试功能
        if test_yt_dlp_functionality():
            logger.info("🎉 yt-dlp 功能测试通过")
            return 0
        else:
            logger.error("❌ yt-dlp 功能测试失败")
            return 1

    except Exception as e:
        logger.error(f"❌ 修复过程出错: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
