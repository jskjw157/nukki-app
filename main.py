#!/usr/bin/env python3
"""
누끼 메이커 - AI 기반 제품 이미지 배경 제거 앱
"""
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from ui.app_window import NukkiApp


def main():
    """앱 실행"""
    app = NukkiApp()
    app.mainloop()


if __name__ == "__main__":
    main()

