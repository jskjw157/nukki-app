"""
배경 제거 모듈 - rembg 라이브러리를 활용한 이미지 배경 제거
"""
from PIL import Image, ImageFilter
from rembg import remove, new_session
from pathlib import Path
from typing import Optional, Union
import threading


class BackgroundRemover:
    """rembg를 사용한 배경 제거 클래스"""
    
    # 사용 가능한 모델 목록 (품질 순)
    AVAILABLE_MODELS = [
        'birefnet-general',   # 최신 고품질 모델 (추천)
        'isnet-general-use',  # 일반 용도, 높은 품질
        'u2net',              # 기본 모델
        'silueta',            # 빠르고 괜찮은 품질
    ]
    
    def __init__(self, model_name: str = 'birefnet-general'):
        """
        BackgroundRemover 초기화
        
        Args:
            model_name: 사용할 모델 이름 (기본: isnet-general-use)
        """
        self._model_name = model_name
        self._session = None
        self._lock = threading.Lock()
    
    def _get_session(self):
        """세션 가져오기 (지연 로딩)"""
        if self._session is None:
            self._session = new_session(self._model_name)
        return self._session
    
    def remove_background(
        self,
        input_image: Union[str, Path, Image.Image],
        alpha_matting: bool = True,
        alpha_matting_foreground_threshold: int = 270,
        alpha_matting_background_threshold: int = 20,
        alpha_matting_erode_size: int = 15,
        post_process_mask: bool = True
    ) -> Image.Image:
        """
        이미지에서 배경을 제거합니다.
        
        Args:
            input_image: 입력 이미지 (파일 경로 또는 PIL Image 객체)
            alpha_matting: 알파 매팅 사용 여부 (가장자리를 더 부드럽게 처리)
            alpha_matting_foreground_threshold: 전경 임계값 (높을수록 더 많은 영역을 전경으로)
            alpha_matting_background_threshold: 배경 임계값 (낮을수록 더 많은 영역을 배경으로)
            alpha_matting_erode_size: 침식 크기 (가장자리 정교함)
            post_process_mask: 마스크 후처리 여부
            
        Returns:
            배경이 제거된 PIL Image 객체 (RGBA)
        """
        # 입력 이미지 로드
        if isinstance(input_image, (str, Path)):
            img = Image.open(input_image)
        else:
            img = input_image.copy()
        
        # RGB로 변환 (필요한 경우)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 배경 제거
        with self._lock:
            result = remove(
                img,
                session=self._get_session(),
                alpha_matting=alpha_matting,
                alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
                alpha_matting_background_threshold=alpha_matting_background_threshold,
                alpha_matting_erode_size=alpha_matting_erode_size,
                post_process_mask=post_process_mask
            )
        
        # 가장자리 부드럽게 처리
        result = self._smooth_edges(result)
        
        return result
    
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
    ) -> list[Image.Image]:
        """
        여러 이미지에서 배경을 일괄 제거합니다.
        
        Args:
            input_images: 입력 이미지 리스트
            progress_callback: 진행 상황 콜백 함수 (current, total)
            **kwargs: remove_background에 전달할 추가 인자
            
        Returns:
            배경이 제거된 PIL Image 객체 리스트
        """
        results = []
        total = len(input_images)
        
        for i, img in enumerate(input_images):
            result = self.remove_background(img, **kwargs)
            results.append(result)
            
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

