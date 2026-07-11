import tkinter as tk

class FileSelectorApp:
    def __init__(self, root, message):
        """引数として受け取ったメッセージを表示"""
        self.root = root
        self.result = False
        self.root.title("工事検査用PDFファイル作成アプリ")
        self.root.geometry("800x200")  # 高さを少し広げてボタンのスペースを確保
        self.root.protocol("WM_DELETE_WINDOW", self.on_quit_button_click)
        self.root.after(0, self._center_and_bring_to_front)

        # 引数で受け取ったメッセージをラベルに表示
        self.status_label = tk.Label(root, text=message, font=("Arial", 12))
        self.status_label.pack(pady=20)

        # ボタンのフレームを作成して中央に配置
        button_frame = tk.Frame(root)
        button_frame.pack(pady=20)

        # 「続ける」ボタンの追加
        self.continue_button = tk.Button(button_frame, text="     続ける     ", font=("Arial", 16), 
                                          bg="#4CAF50", fg="white", command=self.on_continue_button_click,
                                          relief="raised", bd=3)
        self.continue_button.pack(side=tk.LEFT, padx=20)

        # 「終了」ボタンの追加
        self.quit_button = tk.Button(button_frame, text="     終了     ", font=("Arial", 16), 
                                      bg="#F44336", fg="white", command=self.on_quit_button_click,
                                      relief="raised", bd=3)
        self.quit_button.pack(side=tk.LEFT, padx=20)

    def on_continue_button_click(self):
        """続けるボタンが押された時の処理"""
        print("続けるボタンが押されました。プログラムを継続します。")
        self.result = True
        self.root.quit()  # メインループを終了
        self.root.destroy()  # ウィンドウを破棄

    def on_quit_button_click(self):
        """終了ボタンが押された時の処理"""
        print("終了ボタンが押されました。プログラムを終了します。")
        self.result = False
        self.root.quit()  # メインループを終了
        self.root.destroy()  # ウィンドウを破棄

    def _center_and_bring_to_front(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = max(0, (self.root.winfo_screenwidth() - width) // 2)
        y = max(0, (self.root.winfo_screenheight() - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.lift()
        self.root.focus_force()
        self.root.attributes("-topmost", True)
        self.root.after(200, lambda: self.root.attributes("-topmost", False))

def main(message):
    """親モジュールから引数を渡してウィンドウを表示"""
    root = tk.Tk()
    app = FileSelectorApp(root, message)  # メッセージを引数として渡す
    root.mainloop()
    return app.result

if __name__ == "__main__":
    # 処理に応じたメッセージ
    message = "処理が終わりました。プログラムを続けますか？"
    main(message)  # 引数としてメッセージを渡す


