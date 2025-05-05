import tkinter as tk
from tkinter import filedialog
import os
import sys

def resource_path(relative_path):
    """PyInstaller でのパス対応"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class FileSelectorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("kojiPDF_v1.4.2 工事検査用PDFファイル作成アプリ")

        icon_path = resource_path("smallicon.ico")
        try:
            self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"アイコン設定に失敗しました: {e}")

        frame = tk.Frame(root, height=60)
        frame.pack(padx=10, pady=5, fill=tk.X)
        frame.pack_propagate(False)

        # ✅ トグルっぽく見せるチェックボタン
        toggle_frame = tk.Frame(root)
        toggle_frame.pack(padx=10, pady=5, fill=tk.X)

        self.add_page_var = tk.BooleanVar(value=False)
        self.toggle_button = tk.Checkbutton(
            toggle_frame,
            text="しおり名の語尾にしおりの下に含まれるページ総数を追記する",
            variable=self.add_page_var,
            onvalue=True,
            offvalue=False
        )
        self.toggle_button.pack(anchor="w")

        # ✅ Word・Excel も PDF に変換して結合するかのチェックボタン
        self.convert_office_var = tk.BooleanVar(value=False)
        self.convert_office_button = tk.Checkbutton(
            toggle_frame,
            text="Officeが入っていれば、Word・Excel・PowerPointファイルも PDF に変換して結合する（暫定フォルダを作成するので、会議資料など100MB以下の資料にのみ使用）",
            variable=self.convert_office_var,
            onvalue=True,
            offvalue=False
        )
        self.convert_office_button.pack(anchor="w")

        # ✅ 縮尺指定を有効にするかどうかのチェックボックス
        self.scale_enable_var = tk.BooleanVar(value=False)
        self.scale_enable_button = tk.Checkbutton(
            toggle_frame,
            text="しおりをクリック時のページの横縦33:21の表示エリアを下記の倍率で拡大縮小する。",
            variable=self.scale_enable_var,
            onvalue=True,
            offvalue=False,
            command=self.toggle_scale_spinboxes
        )
        self.scale_enable_button.pack(anchor="w")

        # ✅ 横縦の縮尺指定スピンボックス
        scale_frame = tk.Frame(toggle_frame)
        scale_frame.pack(anchor="w", pady=(5, 0))


        tk.Label(scale_frame, text="横の倍率:").pack(side=tk.LEFT)
        self.scale_x_var = tk.DoubleVar(value=1.0)
        self.scale_x_spinbox = tk.Spinbox(
            scale_frame, from_=0.10, to=2.00, increment=0.05,
            format="%0.2f", textvariable=self.scale_x_var, width=5,
            state="disabled"
        )
        self.scale_x_spinbox.pack(side=tk.LEFT)
        tk.Label(scale_frame, text="縦の倍率:").pack(side=tk.LEFT)
        self.scale_y_var = tk.DoubleVar(value=1.0)
        self.scale_y_spinbox = tk.Spinbox(
            scale_frame, from_=0.10, to=2.00, increment=0.05,
            format="%0.2f", textvariable=self.scale_y_var, width=5,
            state="disabled"
        )
        self.scale_y_spinbox.pack(side=tk.LEFT, padx=(0, 10))

        frame2 = tk.Frame(root)
        frame2.pack(padx=10, pady=15, fill=tk.X)

        self.notice_label = tk.Label(
            frame2,
            text='''機能：工事施工中における受発注者間の情報共有システムで取り扱う電子データを効率的に検査及び確認できるよう、構造化されたしおり付PDFファイルを作成します。
　　　具体的には、選択されたフォルダ内のすべてPDFファイルを結合し、ファイル名をしおり、フォルダ名を親しおりとして追加して一つのPDFファイルとして保存します。
注意：本アプリは、使用しているPythonモジュールによりAGPL-3.0 Licenseが適用されており、オープンソースソフトウェアとして商用利用も可能です。  
　　　ただし、アプリを改変、再配布、またはネットワーク経由で提供する場合、AGPL-3.0の規約に従い、ソースコードを公開する必要があります。  
　　　この義務を遵守しない場合、AGPL-3.0に基づく利用許諾を受けられませんのでご注意ください。''',
            anchor="w",
            justify="left",
            wraplength=1150
        )
        self.notice_label.pack(side=tk.LEFT, padx=10)

        self.folder_button = tk.Button(frame, text="フォルダを選択", bg="lightgray", command=self.select_folder)
        self.folder_button.pack(side=tk.LEFT, padx=10)

        self.folder_label = tk.Label(
            frame, text="未選択", width=30, anchor="w",
            wraplength=200, justify="left"
        )
        self.folder_label.pack(side=tk.LEFT, padx=10)

        self.file_button = tk.Button(frame, text="検査用PDF保存先", bg="lightgray", command=self.select_save_file)
        self.file_button.pack(side=tk.LEFT, padx=10)

        self.file_label = tk.Label(
            frame, text="未選択", width=30, anchor="w",
            wraplength=200, justify="left"
        )
        self.file_label.pack(side=tk.LEFT, padx=10)

        self.run_button = tk.Button(frame, text="PDFファイル\n作成開始", bg="lightgray", command=self.finish)
        self.run_button.pack(side=tk.LEFT, padx=10)

        self.selected_folder = None
        self.selected_file = None
        self.default_folder = os.path.expanduser("~/Documents")

        
        #self.root.update_idletasks()
        #min_w = self.root.winfo_width()
        #min_h = self.root.winfo_height()
        #self.root.minsize(min_w, min_h)
        #ウインドウを真ん中に表示
        #x = (self.root.winfo_screenwidth() - min_w) // 2
        #y = (self.root.winfo_screenheight() - min_h) // 2
        #self.root.geometry(f"+{x}+{y}")

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def toggle_scale_spinboxes(self):
        state = "normal" if self.scale_enable_var.get() else "disabled"
        self.scale_y_spinbox.config(state=state)
        self.scale_x_spinbox.config(state=state)

    def select_folder(self):
        folder = filedialog.askdirectory(
            title="フォルダを選択してください",
            initialdir=self.default_folder
        )
        if folder:
            self.folder_label.config(text=folder)
            self.selected_folder = folder

    def select_save_file(self):
        file = filedialog.asksaveasfilename(
            title="保存するファイルを指定してください",
            defaultextension=".pdf",
            filetypes=[("PDFファイル", "*.pdf")],
            initialdir=self.default_folder,
            initialfile="検査用栞付結合データ.pdf"
        )
        if file:
            self.file_label.config(text=file)
            self.selected_file = file

    def finish(self):
        self.root.destroy()

    def on_closing(self):
        print("ウィンドウが閉じられました。")
        self.selected_folder = None
        self.selected_file = None
        self.root.destroy()

    @property
    def add_page(self):
        return self.add_page_var.get()

    @property
    def convert_office(self):
        return self.convert_office_var.get()

    @property
    def scale_y(self):
        return self.scale_y_var.get()

    @property
    def scale_x(self):
        return self.scale_x_var.get()

    @property
    def scale_enabled(self):
        return self.scale_enable_var.get()

def select_folder_and_file():
    root = tk.Tk()
    app = FileSelectorApp(root)
    root.mainloop()
    return app.selected_folder, app.selected_file, app.add_page, app.convert_office, app.scale_x, app.scale_y, app.scale_enabled

if __name__ == "__main__":
    folder, file, add_page, convert_office, scale_x, scale_y, scale_enabled = select_folder_and_file()
    print(f"選択されたフォルダ: {folder}")
    print(f"保存するファイルのパス: {file}")
    print(f"ページ数をしおりに追加: {'はい' if add_page else 'いいえ'}")
    print(f"Word・Excel を PDF に変換: {'はい' if convert_office else 'いいえ'}")
    print(f"縦の縮尺: {scale_x:.2f}")
    print(f"横の縮尺: {scale_y:.2f}")
    print(f"縮尺適用: {'はい' if scale_enabled else 'いいえ'}")
