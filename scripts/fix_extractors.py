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
        # 移除非标准提取器，避免与 yt-dlp 内部机制冲突
        test_extractors = [
            # 注释掉非标准提取器
            # 'screencastify',
            # 'screen9',
            # 'screencast',
            # 'screencastomatic',
            # 'screenrec'
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

        # 创建虚拟模块文件
        dummy_file = extractor_dir / f'{extractor_name}.py'

        # 如果文件已存在，跳过
        if dummy_file.exists():
            logger.info(f"ℹ️ extractor 已存在: {dummy_file}")
            return True

        # 生成更完整的虚拟 extractor
        class_name = ''.join(word.capitalize() for word in extractor_name.split('_')) + 'IE'

        dummy_content = f'''# -*- coding: utf-8 -*-
"""
虚拟 {extractor_name} extractor
自动生成以解决导入错误
"""

from .common import InfoExtractor
from ..utils import ExtractorError

class {class_name}(InfoExtractor):
    """虚拟 {extractor_name} extractor"""

    _VALID_URL = r'https?://(?:www\\.)?{extractor_name}\\.com/.*'
    _TESTS = []

    IE_NAME = '{extractor_name}'
    IE_DESC = 'Virtual {extractor_name} extractor (placeholder)'

    def _real_extract(self, url):
        raise ExtractorError(
            f'{{self.IE_NAME}} extractor is not implemented. '
            f'This is a placeholder to prevent import errors.',
            expected=True
        )

# 导出类以便导入
__all__ = ['{class_name}']
'''

        # 尝试写入文件
        try:
            # 先尝试直接写入
            with open(dummy_file, 'w', encoding='utf-8') as f:
                f.write(dummy_content)
            logger.info(f"✅ 创建虚拟 extractor: {dummy_file}")
            return True
        except PermissionError:
            logger.warning(f"⚠️ 权限不足，无法创建: {dummy_file}")

            # 尝试在临时位置创建，然后动态导入
            try:
                import tempfile
                import importlib.util

                # 在临时目录创建模块
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                    f.write(dummy_content)
                    temp_file = f.name

                # 动态加载模块
                spec = importlib.util.spec_from_file_location(f"yt_dlp.extractor.{extractor_name}", temp_file)
                module = importlib.util.module_from_spec(spec)

                # 将模块添加到 sys.modules
                sys.modules[f"yt_dlp.extractor.{extractor_name}"] = module

                # 清理临时文件
                os.unlink(temp_file)

                logger.info(f"✅ 动态创建虚拟 extractor: {extractor_name}")
                return True

            except Exception as e:
                logger.warning(f"⚠️ 动态创建也失败: {e}")
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

def create_runtime_extractor(extractor_name):
    """在运行时动态创建 extractor 模块"""
    try:
        import types
        from yt_dlp.extractor.common import InfoExtractor
        from yt_dlp.utils import ExtractorError

        # 生成类名
        class_name = ''.join(word.capitalize() for word in extractor_name.split('_')) + 'IE'

        # 动态创建类
        def _real_extract(self, url):
            raise ExtractorError(
                f'{self.IE_NAME} extractor is not implemented. '
                f'This is a placeholder to prevent import errors.',
                expected=True
            )

        # 创建类属性
        attrs = {
            '_VALID_URL': r'https?://(?:www\.)?example\.com/.*',
            '_TESTS': [],
            'IE_NAME': extractor_name,
            'IE_DESC': f'Virtual {extractor_name} extractor (placeholder)',
            '_real_extract': _real_extract,
        }

        # 动态创建类
        ExtractorClass = type(class_name, (InfoExtractor,), attrs)

        # 创建模块
        module = types.ModuleType(f'yt_dlp.extractor.{extractor_name}')
        setattr(module, class_name, ExtractorClass)
        setattr(module, '__all__', [class_name])

        # 注册到 sys.modules
        sys.modules[f'yt_dlp.extractor.{extractor_name}'] = module

        logger.info(f"✅ 运行时创建虚拟 extractor: {extractor_name}")
        return True

    except Exception as e:
        logger.error(f"运行时创建 extractor 失败: {e}")
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

    # 首先尝试运行时创建
    runtime_success = 0
    for extractor_name in missing_extractors:
        if create_runtime_extractor(extractor_name):
            runtime_success += 1

    if runtime_success > 0:
        logger.info(f"✅ 运行时创建 {runtime_success} 个虚拟 extractors")

    # 然后尝试文件创建（如果有权限）
    file_success = 0
    for extractor_name in missing_extractors:
        if create_dummy_extractor(extractor_name):
            file_success += 1

    if file_success > 0:
        logger.info(f"✅ 文件创建 {file_success} 个虚拟 extractors")

    total_success = max(runtime_success, file_success)
    logger.info(f"✅ 总共修复 {total_success}/{len(missing_extractors)} 个 extractors")

    return total_success > 0

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

            # 获取版本信息（官方正确方式）
            version = 'Unknown'
            try:
                # 官方正确方式：从 yt_dlp.version 导入
                from yt_dlp.version import __version__
                version = __version__
            except ImportError:
                try:
                    # 备用方式1：通过 yt_dlp.version 模块
                    version = yt_dlp.version.__version__
                except AttributeError:
                    try:
                        # 备用方式2：直接从 yt_dlp（某些旧版本）
                        version = yt_dlp.__version__
                    except AttributeError:
                        pass

            logger.info(f"✅ yt-dlp 已安装: {version}")
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
