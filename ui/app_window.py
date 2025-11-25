"""
메인 GUI 윈도우 - CustomTkinter 기반 누끼 앱
"""
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageDraw
from pathlib import Path
from typing import Optional
import threading
import json

from core.background_remover import get_remover
from core.gemini_processor import get_processor

# 설정 파일 경로
CONFIG_FILE = Path.home() / '.nukki_config.json'


class ImageCard(ctk.CTkFrame):
    """이미지 카드 위젯 - 원본과 결과 이미지를 표시"""
    
    def __init__(self, master, image_path: str, on_preview_click=None, **kwargs):
        super().__init__(master, **kwargs)
        
        self.image_path = image_path
        self.original_image: Optional[Image.Image] = None
        self.result_image: Optional[Image.Image] = None
        self.is_processed = False
        self.is_selected = ctk.BooleanVar(value=True)  # 기본 선택됨
        self.on_preview_click = on_preview_click
        
        self.configure(
            corner_radius=12,
            fg_color=("#e8e8e8", "#2b2b2b"),
            border_width=2,
            border_color=("#c0c0c0", "#404040")
        )
        
        self._setup_ui()
        self._load_image()
    
    def _setup_ui(self):
        """UI 구성"""
        # 상단 행 (체크박스 + 파일명)
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", pady=(8, 3), padx=8)
        
        # 체크박스
        self.checkbox = ctk.CTkCheckBox(
            top_frame,
            text="",
            variable=self.is_selected,
            width=24,
            height=24,
            corner_radius=4,
            fg_color=("#3b82f6", "#2563eb"),
            hover_color=("#2563eb", "#1d4ed8")
        )
        self.checkbox.pack(side="left")
        
        # 파일명 라벨
        filename = Path(self.image_path).name
        if len(filename) > 20:
            filename = filename[:17] + "..."
        
        self.name_label = ctk.CTkLabel(
            top_frame,
            text=filename,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#333333", "#ffffff")
        )
        self.name_label.pack(side="left", padx=5)
        
        # 이미지 프레임 (클릭 가능)
        self.image_frame = ctk.CTkFrame(
            self,
            fg_color=("#ffffff", "#1a1a1a"),
            corner_radius=8,
            width=200,
            height=180
        )
        self.image_frame.pack(pady=3, padx=10)
        self.image_frame.pack_propagate(False)
        
        # 이미지 라벨
        self.image_label = ctk.CTkLabel(
            self.image_frame,
            text="로딩 중...",
            font=ctk.CTkFont(size=11),
            cursor="hand2"  # 클릭 가능함을 표시
        )
        self.image_label.place(relx=0.5, rely=0.5, anchor="center")
        self.image_label.bind("<Button-1>", self._on_image_click)
        
        # 하단 행 (상태 + 저장 버튼)
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", pady=(3, 8), padx=8)
        
        # 상태 라벨
        self.status_label = ctk.CTkLabel(
            bottom_frame,
            text="대기 중",
            font=ctk.CTkFont(size=10),
            text_color=("#666666", "#aaaaaa")
        )
        self.status_label.pack(side="left")
        
        # 개별 저장 버튼 (처리 완료 후 표시)
        self.save_button = ctk.CTkButton(
            bottom_frame,
            text="💾",
            width=30,
            height=24,
            corner_radius=4,
            font=ctk.CTkFont(size=12),
            fg_color=("#10b981", "#059669"),
            hover_color=("#059669", "#047857"),
            command=self._save_individual
        )
        # 처음에는 숨김
        
    def _on_image_click(self, event):
        """이미지 클릭 시 미리보기 열기"""
        if self.on_preview_click:
            image_to_show = self.result_image if self.is_processed else self.original_image
            if image_to_show:
                self.on_preview_click(image_to_show, Path(self.image_path).name)
    
    def _save_individual(self):
        """개별 이미지 저장"""
        if not self.result_image:
            return
        
        # 저장 경로 선택
        original_name = Path(self.image_path).stem
        save_path = filedialog.asksaveasfilename(
            title="이미지 저장",
            defaultextension=".png",
            initialfile=f"{original_name}_nukki.png",
            filetypes=[("PNG 파일", "*.png"), ("모든 파일", "*.*")]
        )
        
        if save_path:
            try:
                self.result_image.save(save_path, format='PNG')
                messagebox.showinfo("완료", f"저장되었습니다!\n{save_path}")
            except Exception as e:
                messagebox.showerror("오류", f"저장 실패: {e}")
    
    def _load_image(self):
        """이미지 로드 및 표시"""
        try:
            self.original_image = Image.open(self.image_path)
            self._display_image(self.original_image)
        except Exception as e:
            self.image_label.configure(text=f"로드 실패\n{str(e)[:20]}")
    
    def _display_image(self, image: Image.Image):
        """이미지를 라벨에 표시"""
        # 썸네일 크기로 리사이즈
        display_img = image.copy()
        display_img.thumbnail((180, 180), Image.Resampling.LANCZOS)
        
        # 체커보드 배경 생성 (투명도 표시용)
        if display_img.mode == 'RGBA':
            checker = self._create_checker_background(display_img.size)
            checker.paste(display_img, mask=display_img.split()[3])
            display_img = checker
        
        # CTkImage로 변환
        ctk_image = ctk.CTkImage(
            light_image=display_img,
            dark_image=display_img,
            size=display_img.size
        )
        
        self.image_label.configure(image=ctk_image, text="")
        self.image_label.image = ctk_image  # 참조 유지
    
    def _create_checker_background(self, size: tuple) -> Image.Image:
        """체커보드 배경 생성 (투명도 시각화) - 최적화된 버전"""
        block_size = 10
        checker = Image.new('RGB', size, '#ffffff')
        draw = ImageDraw.Draw(checker)
        
        # 회색 블록만 그리기 (더 효율적)
        for y in range(0, size[1], block_size):
            for x in range(0, size[0], block_size):
                if (x // block_size + y // block_size) % 2:
                    draw.rectangle(
                        [x, y, min(x + block_size, size[0]), min(y + block_size, size[1])],
                        fill=(200, 200, 200)
                    )
        
        return checker
    
    def set_status(self, status: str, color: Optional[str] = None):
        """상태 업데이트"""
        self.status_label.configure(text=status)
        if color:
            self.status_label.configure(text_color=color)
    
    def set_result(self, image: Image.Image):
        """결과 이미지 설정"""
        self.result_image = image
        self.is_processed = True
        self._display_image(image)
        self.set_status("완료 ✓", "#22c55e")
        
        # 테두리 색상 변경
        self.configure(border_color=("#22c55e", "#22c55e"))
        
        # 개별 저장 버튼 표시
        self.save_button.pack(side="right")


class NukkiApp(ctk.CTk):
    """메인 애플리케이션 윈도우"""
    
    def __init__(self):
        super().__init__()
        
        # 윈도우 설정
        self.title("누끼 메이커 - AI 배경 제거")
        self.geometry("1200x800")
        self.minsize(900, 600)
        
        # 테마 설정 (시스템 설정 따르기)
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")
        
        # 상태 변수
        self.image_cards: list[ImageCard] = []
        self.api_key: str = ""
        self.use_gemini = ctk.BooleanVar(value=False)
        self.select_all_var = ctk.BooleanVar(value=True)  # 전체 선택
        self.quality_var = ctk.StringVar(value="normal")  # 품질 모드
        self.auto_detect_var = ctk.BooleanVar(value=True)  # 인물 자동 감지
        self.processing = False
        
        # 저장된 API 키 로드
        self._load_config()
        
        self._setup_ui()
    
    def _setup_ui(self):
        """메인 UI 구성"""
        # 메인 컨테이너
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 헤더
        self._create_header()
        
        # 컨텐츠 영역
        self._create_content_area()
        
        # 하단 컨트롤
        self._create_controls()
    
    def _create_header(self):
        """헤더 영역 생성"""
        header_frame = ctk.CTkFrame(
            self.main_container,
            fg_color=("#f0f4ff", "#1e293b"),
            corner_radius=16,
            height=100
        )
        header_frame.pack(fill="x", pady=(0, 15))
        header_frame.pack_propagate(False)
        
        # 타이틀
        title_label = ctk.CTkLabel(
            header_frame,
            text="✨ 누끼 메이커",
            font=ctk.CTkFont(family="Pretendard", size=28, weight="bold"),
            text_color=("#1e40af", "#60a5fa")
        )
        title_label.pack(side="left", padx=30, pady=25)
        
        # 서브타이틀
        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="AI 기반 제품 이미지 배경 제거",
            font=ctk.CTkFont(size=14),
            text_color=("#64748b", "#94a3b8")
        )
        subtitle_label.pack(side="left", pady=25)
        
        # API 키 설정 버튼
        self.api_button = ctk.CTkButton(
            header_frame,
            text="⚙️ API 설정",
            font=ctk.CTkFont(size=13),
            width=140,
            height=36,
            corner_radius=8,
            fg_color=("#6366f1", "#4f46e5"),
            hover_color=("#4f46e5", "#4338ca"),
            command=self._show_api_dialog
        )
        self.api_button.pack(side="right", padx=30, pady=25)
        
        # 저장된 API 키가 있으면 버튼 상태 업데이트
        self._update_api_button_status()
    
    def _create_content_area(self):
        """컨텐츠 영역 생성"""
        content_frame = ctk.CTkFrame(
            self.main_container,
            fg_color="transparent"
        )
        content_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        # 드롭 영역 / 이미지 그리드
        self.drop_frame = ctk.CTkFrame(
            content_frame,
            fg_color=("#f8fafc", "#0f172a"),
            corner_radius=16,
            border_width=3,
            border_color=("#cbd5e1", "#334155")
        )
        self.drop_frame.pack(fill="both", expand=True)
        
        # 스크롤 가능한 이미지 그리드
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self.drop_frame,
            fg_color="transparent",
            corner_radius=0
        )
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 초기 안내
        self.drop_label = ctk.CTkLabel(
            self.scrollable_frame,
            text="📁 이미지를 선택하세요\n\n지원 형식: JPG, PNG, WEBP, BMP",
            font=ctk.CTkFont(size=16),
            text_color=("#94a3b8", "#64748b"),
            justify="center"
        )
        self.drop_label.pack(expand=True, pady=100)
        
        # 파일 선택 버튼
        self.initial_select_button = ctk.CTkButton(
            self.scrollable_frame,
            text="📂 이미지 선택",
            font=ctk.CTkFont(size=14, weight="bold"),
            width=200,
            height=45,
            corner_radius=10,
            fg_color=("#3b82f6", "#2563eb"),
            hover_color=("#2563eb", "#1d4ed8"),
            command=self._select_files
        )
        self.initial_select_button.pack(pady=(0, 100))
    
    def _create_controls(self):
        """하단 컨트롤 영역 생성"""
        control_frame = ctk.CTkFrame(
            self.main_container,
            fg_color=("#f0f4ff", "#1e293b"),
            corner_radius=16,
            height=80
        )
        control_frame.pack(fill="x")
        control_frame.pack_propagate(False)
        
        # 왼쪽 옵션
        left_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        left_frame.pack(side="left", padx=20, pady=15)
        
        # 전체 선택 체크박스
        self.select_all_checkbox = ctk.CTkCheckBox(
            left_frame,
            text="전체 선택",
            font=ctk.CTkFont(size=12),
            variable=self.select_all_var,
            onvalue=True,
            offvalue=False,
            corner_radius=4,
            fg_color=("#3b82f6", "#2563eb"),
            hover_color=("#2563eb", "#1d4ed8"),
            command=self._toggle_select_all
        )
        self.select_all_checkbox.pack(side="left", padx=(0, 10))
        
        # 품질 선택 라벨
        quality_label = ctk.CTkLabel(
            left_frame,
            text="품질:",
            font=ctk.CTkFont(size=12),
            text_color=("#64748b", "#94a3b8")
        )
        quality_label.pack(side="left", padx=(0, 3))
        
        # 품질 선택 드롭다운
        self.quality_dropdown = ctk.CTkOptionMenu(
            left_frame,
            variable=self.quality_var,
            values=["fast", "normal", "high"],
            width=90,
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color=("#3b82f6", "#2563eb"),
            button_color=("#2563eb", "#1d4ed8"),
            button_hover_color=("#1d4ed8", "#1e40af"),
            dropdown_fg_color=("#f8fafc", "#1e293b"),
            dropdown_hover_color=("#e2e8f0", "#334155")
        )
        self.quality_dropdown.pack(side="left", padx=(0, 10))
        
        # 인물 자동감지 체크박스
        self.auto_detect_checkbox = ctk.CTkCheckBox(
            left_frame,
            text="인물감지",
            font=ctk.CTkFont(size=12),
            variable=self.auto_detect_var,
            onvalue=True,
            offvalue=False,
            corner_radius=4,
            fg_color=("#f59e0b", "#d97706"),
            hover_color=("#d97706", "#b45309")
        )
        self.auto_detect_checkbox.pack(side="left", padx=(0, 10))
        
        # Gemini 후처리 체크박스
        self.gemini_checkbox = ctk.CTkCheckBox(
            left_frame,
            text="AI 후처리",
            font=ctk.CTkFont(size=12),
            variable=self.use_gemini,
            onvalue=True,
            offvalue=False,
            corner_radius=4,
            fg_color=("#6366f1", "#4f46e5"),
            hover_color=("#4f46e5", "#4338ca")
        )
        self.gemini_checkbox.pack(side="left")
        
        # 상태 라벨
        self.status_label = ctk.CTkLabel(
            left_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=("#64748b", "#94a3b8")
        )
        self.status_label.pack(side="left", padx=15)
        
        # 오른쪽 버튼들
        right_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        right_frame.pack(side="right", padx=20, pady=15)
        
        # 이미지 추가 버튼
        add_button = ctk.CTkButton(
            right_frame,
            text="➕ 추가",
            font=ctk.CTkFont(size=12),
            width=80,
            height=36,
            corner_radius=8,
            fg_color=("#3b82f6", "#2563eb"),
            hover_color=("#2563eb", "#1d4ed8"),
            command=self._select_files
        )
        add_button.pack(side="left", padx=3)
        
        # 선택 삭제 버튼
        delete_selected_button = ctk.CTkButton(
            right_frame,
            text="🗑️ 선택삭제",
            font=ctk.CTkFont(size=12),
            width=90,
            height=36,
            corner_radius=8,
            fg_color=("#ef4444", "#dc2626"),
            hover_color=("#dc2626", "#b91c1c"),
            command=self._delete_selected
        )
        delete_selected_button.pack(side="left", padx=3)
        
        # 저장 버튼
        save_button = ctk.CTkButton(
            right_frame,
            text="💾 모두 저장",
            font=ctk.CTkFont(size=12),
            width=100,
            height=36,
            corner_radius=8,
            fg_color=("#10b981", "#059669"),
            hover_color=("#059669", "#047857"),
            command=self._save_all
        )
        save_button.pack(side="left", padx=3)
        
        # 처리 버튼
        self.process_button = ctk.CTkButton(
            right_frame,
            text="🚀 누끼 따기",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=130,
            height=42,
            corner_radius=10,
            fg_color=("#8b5cf6", "#7c3aed"),
            hover_color=("#7c3aed", "#6d28d9"),
            command=self._process_images
        )
        self.process_button.pack(side="left", padx=(8, 0))
    
    def _select_files(self):
        """파일 선택 다이얼로그"""
        filetypes = [
            ("이미지 파일", "*.png *.jpg *.jpeg *.webp *.bmp"),
            ("모든 파일", "*.*")
        ]
        
        files = filedialog.askopenfilenames(
            title="이미지 선택",
            filetypes=filetypes
        )
        
        if files:
            self._add_images(list(files))
    
    def _add_images(self, file_paths: list[str]):
        """이미지 추가"""
        # 초기 안내 위젯 제거 (첫 번째 호출에서만)
        if not hasattr(self, '_initial_widgets_removed'):
            try:
                self.drop_label.destroy()
                self.initial_select_button.destroy()
            except:
                pass
            self._initial_widgets_removed = True
        
        # 새 카드들 생성 (위치 지정 없이)
        for path in file_paths:
            card = ImageCard(
                self.scrollable_frame,
                path,
                on_preview_click=self._show_preview,
                width=240,
                height=290
            )
            self.image_cards.append(card)
        
        # 전체 카드 재배치
        self._rearrange_cards()
        self._update_status(f"{len(self.image_cards)}개 이미지 로드됨")
    
    def _toggle_select_all(self):
        """전체 선택/해제"""
        select_all = self.select_all_var.get()
        for card in self.image_cards:
            card.is_selected.set(select_all)
    
    def _delete_selected(self):
        """선택된 이미지 삭제"""
        if self.processing:
            messagebox.showwarning("알림", "처리 중에는 삭제할 수 없습니다.")
            return
        
        selected_cards = [c for c in self.image_cards if c.is_selected.get()]
        
        if not selected_cards:
            messagebox.showwarning("알림", "삭제할 이미지를 선택하세요.")
            return
        
        # 선택된 카드 삭제
        for card in selected_cards:
            card.destroy()
            self.image_cards.remove(card)
        
        # 남은 카드 재배치
        self._rearrange_cards()
        
        # 모두 삭제되면 초기 화면으로
        if not self.image_cards:
            self._clear_all()
        else:
            self._update_status(f"{len(self.image_cards)}개 이미지 남음")
    
    def _rearrange_cards(self):
        """카드 그리드 재배치 (한 행에 4개씩, 꽉 차면 다음 행으로)"""
        # 그리드 열 설정
        for c in range(4):
            self.scrollable_frame.grid_columnconfigure(c, weight=1, uniform="card_col")
        
        # 모든 카드 재배치
        for idx, card in enumerate(self.image_cards):
            card.grid_forget()  # 기존 배치 제거
            row = idx // 4      # 행 번호
            col = idx % 4       # 열 번호 (0-3)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="n")
    
    def _show_preview(self, image: Image.Image, title: str):
        """이미지 미리보기 팝업"""
        preview_window = ctk.CTkToplevel(self)
        preview_window.title(f"미리보기 - {title}")
        preview_window.geometry("800x600")
        preview_window.transient(self)
        preview_window.grab_set()
        
        # 이미지 크기 조정 (창에 맞게)
        display_img = image.copy()
        display_img.thumbnail((750, 550), Image.Resampling.LANCZOS)
        
        # 체커보드 배경 (투명도 표시)
        if display_img.mode == 'RGBA':
            checker = self._create_checker_for_preview(display_img.size)
            checker.paste(display_img, mask=display_img.split()[3])
            display_img = checker
        
        # CTkImage로 변환
        ctk_image = ctk.CTkImage(
            light_image=display_img,
            dark_image=display_img,
            size=display_img.size
        )
        
        # 이미지 라벨
        image_label = ctk.CTkLabel(
            preview_window,
            image=ctk_image,
            text=""
        )
        image_label.pack(expand=True, pady=20)
        image_label.image = ctk_image
        
        # 닫기 버튼
        close_button = ctk.CTkButton(
            preview_window,
            text="닫기",
            width=100,
            command=preview_window.destroy
        )
        close_button.pack(pady=10)
    
    def _create_checker_for_preview(self, size: tuple) -> Image.Image:
        """미리보기용 체커보드 배경"""
        block_size = 15
        checker = Image.new('RGB', size, '#ffffff')
        draw = ImageDraw.Draw(checker)
        
        for y in range(0, size[1], block_size):
            for x in range(0, size[0], block_size):
                if (x // block_size + y // block_size) % 2:
                    draw.rectangle(
                        [x, y, min(x + block_size, size[0]), min(y + block_size, size[1])],
                        fill=(220, 220, 220)
                    )
        return checker
    
    def _process_images(self):
        """이미지 처리 시작 (선택된 이미지만)"""
        # 선택된 미처리 이미지만 필터링
        selected_cards = [c for c in self.image_cards if c.is_selected.get() and not c.is_processed]
        
        if not selected_cards:
            messagebox.showwarning("알림", "처리할 이미지가 없습니다.\n(선택되지 않았거나 이미 처리됨)")
            return
        
        if self.processing:
            return
        
        # Gemini 사용 시 API 키 확인
        if self.use_gemini.get() and not self.api_key:
            messagebox.showwarning("알림", "Gemini 후처리를 사용하려면 API 키를 설정하세요.")
            self._show_api_dialog()
            return
        
        self.processing = True
        self.process_button.configure(state="disabled", text="처리 중...")
        
        # 별도 스레드에서 처리
        thread = threading.Thread(target=self._process_thread, daemon=True)
        thread.start()
    
    def _process_thread(self):
        """백그라운드에서 이미지 처리 (선택된 것만)"""
        remover = get_remover()
        processor = get_processor() if self.use_gemini.get() else None
        
        if processor and self.api_key:
            processor.set_api_key(self.api_key)
        
        # 선택된 미처리 카드만 처리
        cards_to_process = [c for c in self.image_cards if c.is_selected.get() and not c.is_processed]
        total = len(cards_to_process)
        
        for i, card in enumerate(cards_to_process):
            
            try:
                # 상태 업데이트
                self.after(0, lambda c=card: c.set_status("처리 중...", "#f59e0b"))
                self.after(0, lambda idx=i+1, t=total: self._update_status(f"처리 중... ({idx}/{t})"))
                
                # 배경 제거 (선택된 품질 모드 + 인물 자동 감지)
                quality = self.quality_var.get()
                auto_detect = self.auto_detect_var.get()
                result, is_person = remover.remove_background(
                    card.image_path, 
                    quality=quality,
                    auto_detect_person=auto_detect
                )
                
                # 인물 감지 시 상태 표시
                if is_person:
                    self.after(0, lambda c=card: c.set_status("인물 감지됨 👤", "#f59e0b"))
                
                # Gemini 후처리 (선택적)
                if processor and self.use_gemini.get():
                    self.after(0, lambda c=card: c.set_status("AI 분석 중...", "#8b5cf6"))
                    try:
                        enhanced = processor.enhance_edges(result)
                        if enhanced:
                            result = enhanced
                    except Exception as e:
                        print(f"Gemini 후처리 오류: {e}")
                
                # 결과 표시
                self.after(0, lambda c=card, r=result: c.set_result(r))
                
            except Exception as e:
                self.after(0, lambda c=card, err=str(e): c.set_status(f"오류: {err[:15]}", "#ef4444"))
        
        # 완료
        self.after(0, self._processing_complete)
    
    def _processing_complete(self):
        """처리 완료"""
        self.processing = False
        self.process_button.configure(state="normal", text="🚀 누끼 따기")
        
        processed = sum(1 for card in self.image_cards if card.is_processed)
        self._update_status(f"완료! {processed}개 이미지 처리됨")
    
    def _save_all(self):
        """모든 결과 저장"""
        processed_cards = [c for c in self.image_cards if c.is_processed]
        
        if not processed_cards:
            messagebox.showwarning("알림", "저장할 이미지가 없습니다. 먼저 누끼를 따주세요.")
            return
        
        # 저장 폴더 선택
        save_dir = filedialog.askdirectory(title="저장 폴더 선택")
        
        if not save_dir:
            return
        
        remover = get_remover()
        saved_count = 0
        
        for card in processed_cards:
            if card.result_image:
                # 파일명 생성 (원본명_nukki.png)
                original_name = Path(card.image_path).stem
                output_path = Path(save_dir) / f"{original_name}_nukki.png"
                
                try:
                    remover.save_result(card.result_image, output_path)
                    saved_count += 1
                except Exception as e:
                    print(f"저장 실패: {e}")
        
        messagebox.showinfo("완료", f"{saved_count}개 이미지가 저장되었습니다.\n\n저장 위치: {save_dir}")
    
    def _clear_all(self):
        """모든 이미지 초기화"""
        if self.processing:
            messagebox.showwarning("알림", "처리 중에는 초기화할 수 없습니다.")
            return
        
        for card in self.image_cards:
            card.destroy()
        
        self.image_cards.clear()
        
        # 초기 위젯 플래그 초기화 (다시 초기 화면 표시 가능하도록)
        if hasattr(self, '_initial_widgets_removed'):
            delattr(self, '_initial_widgets_removed')
        
        # 안내 다시 표시
        self.drop_label = ctk.CTkLabel(
            self.scrollable_frame,
            text="📁 이미지를 선택하세요\n\n지원 형식: JPG, PNG, WEBP, BMP",
            font=ctk.CTkFont(size=16),
            text_color=("#94a3b8", "#64748b"),
            justify="center"
        )
        self.drop_label.pack(expand=True, pady=100)
        
        self.initial_select_button = ctk.CTkButton(
            self.scrollable_frame,
            text="📂 이미지 선택",
            font=ctk.CTkFont(size=14, weight="bold"),
            width=200,
            height=45,
            corner_radius=10,
            fg_color=("#3b82f6", "#2563eb"),
            hover_color=("#2563eb", "#1d4ed8"),
            command=self._select_files
        )
        self.initial_select_button.pack(pady=(0, 100))
        
        self._update_status("")
    
    def _load_config(self):
        """저장된 설정 로드"""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.api_key = config.get('api_key', '')
        except Exception as e:
            print(f"설정 로드 실패: {e}")
    
    def _save_config(self):
        """설정 저장"""
        try:
            config = {'api_key': self.api_key}
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"설정 저장 실패: {e}")
    
    def _update_api_button_status(self):
        """API 버튼 상태 업데이트"""
        if self.api_key:
            # API 키가 설정됨 - 녹색으로 변경
            self.api_button.configure(
                text="✓ API 연결됨",
                fg_color=("#10b981", "#059669"),
                hover_color=("#059669", "#047857")
            )
        else:
            # API 키가 없음 - 기본 색상
            self.api_button.configure(
                text="⚙️ API 설정",
                fg_color=("#6366f1", "#4f46e5"),
                hover_color=("#4f46e5", "#4338ca")
            )
    
    def _show_api_dialog(self):
        """API 키 설정 다이얼로그"""
        # 현재 API 키 상태 표시
        current_status = "현재: 설정됨 ✓" if self.api_key else "현재: 미설정"
        
        dialog = ctk.CTkInputDialog(
            text=f"Google Gemini API 키를 입력하세요:\n\n(https://aistudio.google.com에서 발급)\n\n{current_status}\n\n입력한 키는 자동으로 저장됩니다.",
            title="API 키 설정"
        )
        
        key = dialog.get_input()
        
        if key and key.strip():
            new_key = key.strip()
            
            # API 키 유효성 검증
            if self._validate_api_key(new_key):
                self.api_key = new_key
                self._save_config()  # 설정 파일에 저장
                self._update_api_button_status()  # 버튼 상태 업데이트
                messagebox.showinfo("완료", "API 키가 확인되었습니다! ✓\n\n저장 완료.")
            else:
                messagebox.showerror("오류", "API 키가 유효하지 않습니다.\n\n올바른 키인지 확인해주세요.")
    
    def _validate_api_key(self, api_key: str) -> bool:
        """API 키 유효성 검증"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            # 간단한 테스트 요청
            response = model.generate_content("Hi")
            return response is not None
        except Exception as e:
            print(f"API 키 검증 실패: {e}")
            return False
    
    def _update_status(self, message: str):
        """상태 메시지 업데이트"""
        self.status_label.configure(text=message)

