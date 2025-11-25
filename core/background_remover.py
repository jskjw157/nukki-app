"""
배경 제거 모듈 - rembg 라이브러리를 활용한 이미지 배경 제거
"""
from PIL import Image, ImageFilter
from rembg import remove, new_session
from pathlib import Path
from typing import Optional, Union
import threading
import cv2
import numpy as np


class BackgroundRemover:
    """rembg를 사용한 배경 제거 클래스"""
    
    # 사용 가능한 모델 목록 (품질 순)
    AVAILABLE_MODELS = [
        'birefnet-general',   # 최신 고품질 모델 (추천)
        'birefnet-portrait',  # 인물 전용 모델 (머리카락 등 디테일)
        'isnet-general-use',  # 일반 용도, 높은 품질
        'u2net',              # 기본 모델
        'silueta',            # 빠르고 괜찮은 품질
    ]
    
    # 인물용 모델
    PORTRAIT_MODEL = 'birefnet-portrait'
    
    # 품질 프리셋 (머리카락 등 디테일 보존 최적화)
    QUALITY_PRESETS = {
        'fast': {  # 빠름 - 디테일 적음
            'alpha_matting': False,
            'foreground_threshold': 240,
            'background_threshold': 10,
            'erode_size': 10,
            'blur_radius': 0
        },
        'normal': {  # 일반 - 균형
            'alpha_matting': True,
            'foreground_threshold': 240,
            'background_threshold': 10,
            'erode_size': 10,
            'blur_radius': 0.5
        },
        'high': {  # 고품질 - 머리카락 등 디테일 최대 보존
            'alpha_matting': True,
            'foreground_threshold': 220,
            'background_threshold': 5,
            'erode_size': 5,
            'blur_radius': 0.3
        }
    }
    
    def __init__(self, model_name: str = 'birefnet-general'):
        """
        BackgroundRemover 초기화
        
        Args:
            model_name: 사용할 모델 이름 (기본: birefnet-general)
        """
        self._model_name = model_name
        self._session = None
        self._portrait_session = None  # 인물용 모델 세션
        self._lock = threading.Lock()
        self._face_cascade = None  # 얼굴 감지용 cascade
    
    def _get_session(self, use_portrait: bool = False):
        """세션 가져오기 (지연 로딩)"""
        if use_portrait:
            if self._portrait_session is None:
                self._portrait_session = new_session(self.PORTRAIT_MODEL)
            return self._portrait_session
        else:
            if self._session is None:
                self._session = new_session(self._model_name)
            return self._session
    
    def _get_face_cascade(self):
        """얼굴 감지용 Haar Cascade 가져오기"""
        if self._face_cascade is None:
            self._face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
        return self._face_cascade
    
    def detect_person(self, image: Image.Image) -> bool:
        """
        OpenCV로 얼굴을 감지하여 인물 사진인지 판단합니다.
        
        Args:
            image: PIL Image 객체
            
        Returns:
            인물 사진이면 True, 아니면 False
        """
        try:
            # PIL -> OpenCV 변환
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # 얼굴 감지
            face_cascade = self._get_face_cascade()
            faces = face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1, 
                minNeighbors=4,
                minSize=(30, 30)
            )
            
            return len(faces) > 0
        except Exception as e:
            print(f"얼굴 감지 오류: {e}")
            return False
    
    def remove_background(
        self,
        input_image: Union[str, Path, Image.Image],
        quality: str = 'normal',
        auto_detect_person: bool = False,
        post_process_mask: bool = True
    ) -> tuple[Image.Image, bool]:
        """
        이미지에서 배경을 제거합니다.
        
        Args:
            input_image: 입력 이미지 (파일 경로 또는 PIL Image 객체)
            quality: 품질 모드 ('fast', 'normal', 'high')
            auto_detect_person: 인물 자동 감지 여부
            post_process_mask: 마스크 후처리 여부
            
        Returns:
            (배경이 제거된 PIL Image 객체, 인물 감지 여부)
        """
        # 품질 프리셋 가져오기
        preset = self.QUALITY_PRESETS.get(quality, self.QUALITY_PRESETS['normal'])
        
        # 입력 이미지 로드
        if isinstance(input_image, (str, Path)):
            img = Image.open(input_image)
        else:
            img = input_image.copy()
        
        # RGB로 변환 (필요한 경우)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 인물 감지 (auto_detect_person이 True인 경우)
        is_person = False
        if auto_detect_person:
            is_person = self.detect_person(img)
        
        # 배경 제거 (인물이면 portrait 모델 사용)
        with self._lock:
            result = remove(
                img,
                session=self._get_session(use_portrait=is_person),
                alpha_matting=preset['alpha_matting'],
                alpha_matting_foreground_threshold=preset['foreground_threshold'],
                alpha_matting_background_threshold=preset['background_threshold'],
                alpha_matting_erode_size=preset['erode_size'],
                post_process_mask=post_process_mask
            )
        
        # 가장자리 부드럽게 처리 (blur_radius가 0보다 클 때만)
        if preset['blur_radius'] > 0:
            result = self._smooth_edges(result, preset['blur_radius'])
        
        return result, is_person
    
    def _smooth_edges(self, image: Image.Image, blur_radius: float = 1.0) -> Image.Image:
        """
        가장자리를 부드럽게 처리합니다.
        
        Args:
            image: RGBA 이미지
            blur_radius: 블러 강도 (기본: 1.0)
            
        Returns:
            가장자리가 부드러워진 이미지
        """
        if image.mode != 'RGBA':
            return image
        
        # RGB와 Alpha 분리
        r, g, b, a = image.split()
        
        # Alpha 채널만 약간 블러 처리 (가장자리 부드럽게)
        a_smooth = a.filter(ImageFilter.GaussianBlur(blur_radius))
        
        # 다시 합치기
        result = Image.merge('RGBA', (r, g, b, a_smooth))
        
        return result
    
    def remove_background_batch(
        self,
        input_images: list[Union[str, Path, Image.Image]],
        progress_callback: Optional[callable] = None,
        **kwargs
    ) -> list[tuple[Image.Image, bool]]:
        """
        여러 이미지에서 배경을 일괄 제거합니다.
        
        Args:
            input_images: 입력 이미지 리스트
            progress_callback: 진행 상황 콜백 함수 (current, total)
            **kwargs: remove_background에 전달할 추가 인자
            
        Returns:
            (배경이 제거된 PIL Image 객체, 인물 감지 여부) 튜플 리스트
        """
        results = []
        total = len(input_images)
        
        for i, img in enumerate(input_images):
            result, is_person = self.remove_background(img, **kwargs)
            results.append((result, is_person))
            
            if progress_callback:
                progress_callback(i + 1, total)
        
        return results
    
    def save_result(
        self,
        image: Image.Image,
        output_path: Union[str, Path],
        format: str = 'PNG'
    ) -> Path:
        """
        결과 이미지를 파일로 저장합니다.
        
        Args:
            image: 저장할 PIL Image 객체
            output_path: 출력 파일 경로
            format: 이미지 포맷 (기본값: PNG)
            
        Returns:
            저장된 파일 경로
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # PNG 형식으로 저장 (투명 배경 유지)
        image.save(output_path, format=format)
        
        return output_path


# 전역 인스턴스 생성 (싱글톤 패턴)
_remover_instance: Optional[BackgroundRemover] = None


def get_remover() -> BackgroundRemover:
    """BackgroundRemover 싱글톤 인스턴스를 반환합니다."""
    global _remover_instance
    if _remover_instance is None:
        _remover_instance = BackgroundRemover()
    return _remover_instance

