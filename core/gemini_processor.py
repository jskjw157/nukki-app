"""
Gemini API 후처리 모듈 - 이미지 분석 및 품질 평가
"""
import google.generativeai as genai
from PIL import Image, ImageFilter, ImageEnhance
from pathlib import Path
from typing import Optional, Union


class GeminiProcessor:
    """Google Gemini API를 사용한 이미지 분석 및 후처리 클래스"""
    
    # Gemini 모델 설정
    DEFAULT_MODEL = 'gemini-2.5-flash'
    
    def __init__(self, api_key: Optional[str] = None):
        """
        GeminiProcessor 초기화
        
        Args:
            api_key: Google API 키 (없으면 나중에 set_api_key로 설정)
        """
        self._api_key = api_key
        self._model = None
        
        if api_key:
            self._configure(api_key)
    
    def _configure(self, api_key: str):
        """API 설정"""
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(self.DEFAULT_MODEL)
        self._api_key = api_key
    
    def set_api_key(self, api_key: str):
        """
        API 키를 설정합니다.
        
        Args:
            api_key: Google API 키
        """
        self._configure(api_key)
    
    @property
    def is_configured(self) -> bool:
        """API가 설정되었는지 확인"""
        return self._model is not None
    
    def analyze_image(self, image: Union[str, Path, Image.Image]) -> str:
        """
        이미지를 분석하고 품질에 대한 피드백을 제공합니다.
        
        Args:
            image: 분석할 이미지
            
        Returns:
            분석 결과 텍스트
        """
        if not self.is_configured:
            raise ValueError("API 키가 설정되지 않았습니다. set_api_key()를 호출하세요.")
        
        # 이미지 로드
        if isinstance(image, (str, Path)):
            img = Image.open(image)
        else:
            img = image
        
        # Gemini에 이미지 분석 요청
        response = self._model.generate_content([
            "이 제품 이미지의 누끼(배경 제거) 품질을 분석해주세요. "
            "가장자리 처리, 잔여 배경, 전체적인 품질에 대해 평가하고, "
            "개선이 필요한 부분이 있다면 알려주세요. 한국어로 답변해주세요.",
            img
        ])
        
        return response.text
    
    def enhance_edges(
        self,
        image: Union[str, Path, Image.Image],
        auto_enhance: bool = True
    ) -> Optional[Image.Image]:
        """
        Gemini 분석을 기반으로 이미지의 가장자리를 개선합니다.
        
        Gemini가 이미지를 분석하여 품질 문제를 파악하고,
        PIL을 사용해 실제 이미지 개선을 수행합니다.
        
        Args:
            image: 개선할 이미지
            auto_enhance: 자동 개선 적용 여부 (기본값: True)
            
        Returns:
            개선된 이미지
        """
        # 이미지 로드
        if isinstance(image, (str, Path)):
            img = Image.open(image)
        else:
            img = image.copy()
        
        if not auto_enhance:
            return img
        
        # Gemini API가 설정되어 있으면 분석 수행
        analysis_result = None
        if self.is_configured:
            try:
                analysis_result = self._analyze_for_enhancement(img)
            except Exception as e:
                print(f"Gemini 분석 중 오류: {e}")
        
        # PIL 기반 가장자리 개선 적용
        enhanced = self._apply_edge_enhancement(img, analysis_result)
        
        return enhanced
    
    def _analyze_for_enhancement(self, image: Image.Image) -> dict:
        """Gemini를 사용해 이미지 분석 및 개선 권장사항 반환"""
        response = self._model.generate_content([
            "이 누끼 이미지를 분석하고 JSON 형식으로만 답변해주세요:\n"
            '{"edge_rough": true/false, "has_halo": true/false, "needs_smoothing": true/false}\n'
            "edge_rough: 가장자리가 거친지\n"
            "has_halo: 가장자리에 흰색/밝은 테두리(할로)가 있는지\n"
            "needs_smoothing: 전체적으로 부드럽게 처리가 필요한지",
            image
        ])
        
        # JSON 파싱 시도
        try:
            import json
            text = response.text.strip()
            # JSON 부분만 추출
            if '{' in text and '}' in text:
                json_str = text[text.find('{'):text.rfind('}')+1]
                return json.loads(json_str)
        except Exception:
            pass
        
        return {}
    
    def _apply_edge_enhancement(
        self, 
        image: Image.Image, 
        analysis: Optional[dict] = None
    ) -> Image.Image:
        """PIL을 사용한 가장자리 개선"""
        if image.mode != 'RGBA':
            return image
        
        enhanced = image.copy()
        
        # 알파 채널 분리
        r, g, b, a = enhanced.split()
        
        # 기본 개선: 알파 채널 약간 다듬기
        # 가장자리를 더 부드럽게 만들기
        a_smooth = a.filter(ImageFilter.SMOOTH)
        
        # 분석 결과에 따른 추가 처리
        if analysis:
            if analysis.get('has_halo', False):
                # 할로 제거: 알파 경계를 약간 침식
                a_smooth = a_smooth.filter(ImageFilter.MinFilter(3))
            
            if analysis.get('edge_rough', False):
                # 거친 가장자리: 추가 스무딩
                a_smooth = a_smooth.filter(ImageFilter.GaussianBlur(0.5))
        
        # 이미지 재결합
        enhanced = Image.merge('RGBA', (r, g, b, a_smooth))
        
        # 색상 약간 개선
        enhancer = ImageEnhance.Sharpness(enhanced)
        enhanced = enhancer.enhance(1.1)  # 약간의 선명도 증가
        
        return enhanced
    
    def get_quality_score(self, image: Union[str, Path, Image.Image]) -> dict:
        """
        이미지의 누끼 품질 점수를 반환합니다.
        
        Args:
            image: 평가할 이미지
            
        Returns:
            품질 점수 딕셔너리 (edge_quality, transparency, overall)
        """
        if not self.is_configured:
            raise ValueError("API 키가 설정되지 않았습니다. set_api_key()를 호출하세요.")
        
        # 이미지 로드
        if isinstance(image, (str, Path)):
            img = Image.open(image)
        else:
            img = image
        
        response = self._model.generate_content([
            "이 누끼 이미지의 품질을 평가해주세요. 다음 형식으로만 답변해주세요:\n"
            "가장자리: [1-10점]\n"
            "투명도: [1-10점]\n"
            "전체: [1-10점]\n"
            "숫자만 적어주세요.",
            img
        ])
        
        # 응답 파싱
        try:
            lines = response.text.strip().split('\n')
            scores = {}
            for line in lines:
                if '가장자리' in line:
                    scores['edge_quality'] = int(''.join(filter(str.isdigit, line)) or '0')
                elif '투명도' in line:
                    scores['transparency'] = int(''.join(filter(str.isdigit, line)) or '0')
                elif '전체' in line:
                    scores['overall'] = int(''.join(filter(str.isdigit, line)) or '0')
            
            return {
                'edge_quality': scores.get('edge_quality', 0),
                'transparency': scores.get('transparency', 0),
                'overall': scores.get('overall', 0)
            }
        except Exception:
            return {'edge_quality': 0, 'transparency': 0, 'overall': 0}


# 전역 인스턴스
_processor_instance: Optional[GeminiProcessor] = None


def get_processor() -> GeminiProcessor:
    """GeminiProcessor 싱글톤 인스턴스를 반환합니다."""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = GeminiProcessor()
    return _processor_instance

