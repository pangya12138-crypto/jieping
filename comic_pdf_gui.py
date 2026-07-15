
from __future__ import annotations

import hashlib
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


class ComicPDFApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("漫画自动翻页生成 PDF")
        self.geometry("620x480")
        self.resizable(False, False)

        self.url_var = tk.StringVar(value="https://weread.qq.com/")
        self.output_var = tk.StringVar(value=str(Path.home() / "Desktop" / "漫画.pdf"))
        self.wait_var = tk.StringVar(value="1.5")
        self.max_pages_var = tk.StringVar(value="1000")
        self.crop_var = tk.StringVar(value="0.10,0.075,0.80,0.865")
        self.status_var = tk.StringVar(value="等待开始")

        pad = {"padx": 12, "pady": 7}

        ttk.Label(self, text="起始网址").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.url_var, width=56).grid(row=0, column=1, columnspan=2, **pad)

        ttk.Label(self, text="输出 PDF").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.output_var, width=45).grid(row=1, column=1, **pad)
        ttk.Button(self, text="选择", command=self.choose_output).grid(row=1, column=2, **pad)

        ttk.Label(self, text="翻页等待（秒）").grid(row=2, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.wait_var, width=15).grid(row=2, column=1, sticky="w", **pad)

        ttk.Label(self, text="最大页数").grid(row=3, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.max_pages_var, width=15).grid(row=3, column=1, sticky="w", **pad)

        ttk.Label(self, text="裁剪比例").grid(row=4, column=0, sticky="w", **pad)
        ttk.Entry(self, textvariable=self.crop_var, width=32).grid(row=4, column=1, sticky="w", **pad)
        ttk.Label(self, text="左,上,宽,高").grid(row=4, column=2, sticky="w", **pad)

        self.start_btn = ttk.Button(self, text="打开浏览器", command=self.start_browser)
        self.start_btn.grid(row=5, column=0, columnspan=3, pady=15)

        self.continue_btn = ttk.Button(
            self,
            text="已进入正文第一页，开始自动翻页",
            command=self.signal_continue,
            state="disabled",
        )
        self.continue_btn.grid(row=6, column=0, columnspan=3, pady=5)

        ttk.Separator(self).grid(row=7, column=0, columnspan=3, sticky="ew", padx=12, pady=10)

        ttk.Label(
            self,
            text=(
                "使用说明：\n"
                "1. 点击“打开浏览器”。\n"
                "2. 在浏览器中手动登录，并进入漫画正文第一页。\n"
                "3. 回到本程序，点击“开始自动翻页”。\n"
                "4. 程序截图、翻页，最后合并为一个 PDF。\n\n"
                "仅用于你拥有、已购买且平台允许离线保存的内容。"
            ),
            justify="left",
        ).grid(row=8, column=0, columnspan=3, sticky="w", padx=18, pady=5)

        ttk.Label(self, textvariable=self.status_var).grid(
            row=9, column=0, columnspan=3, sticky="w", padx=18, pady=12
        )

        self._continue_event = threading.Event()

    def choose_output(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF 文件", "*.pdf")],
            initialfile="漫画.pdf",
        )
        if path:
            self.output_var.set(path)

    def signal_continue(self):
        self._continue_event.set()
        self.continue_btn.config(state="disabled")
        self.status_var.set("正在自动截图与翻页，请勿操作浏览器……")

    def start_browser(self):
        try:
            wait_seconds = float(self.wait_var.get())
            max_pages = int(self.max_pages_var.get())
            crop = tuple(float(x.strip()) for x in self.crop_var.get().split(","))
            if len(crop) != 4:
                raise ValueError
        except ValueError:
            messagebox.showerror("参数错误", "等待时间、最大页数或裁剪比例格式不正确。")
            return

        self.start_btn.config(state="disabled")
        self.continue_btn.config(state="normal")
        self.status_var.set("浏览器即将打开。请登录并进入正文第一页。")

        args = (
            self.url_var.get().strip(),
            Path(self.output_var.get().strip()),
            wait_seconds,
            max_pages,
            crop,
        )
        threading.Thread(target=self.worker, args=args, daemon=True).start()

    def update_status(self, text):
        self.after(0, lambda: self.status_var.set(text))

    def finish(self, ok, message):
        def _done():
            self.start_btn.config(state="normal")
            self.continue_btn.config(state="disabled")
            self.status_var.set(message)
            if ok:
                messagebox.showinfo("完成", message)
            else:
                messagebox.showerror("失败", message)
        self.after(0, _done)

    @staticmethod
    def crop_image(source: Path, target: Path, crop):
        with Image.open(source) as im:
            w, h = im.size
            left, top, width, height = crop
            box = (
                round(w * left),
                round(h * top),
                round(w * (left + width)),
                round(h * (top + height)),
            )
            im.crop(box).convert("RGB").save(target, quality=95)

    @staticmethod
    def image_hash(path: Path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def images_to_pdf(paths, output):
        images = []
        try:
            for path in paths:
                images.append(Image.open(path).convert("RGB"))
            if not images:
                raise RuntimeError("没有截取到页面。")
            output.parent.mkdir(parents=True, exist_ok=True)
            images[0].save(output, "PDF", save_all=True, append_images=images[1:], resolution=150)
        finally:
            for image in images:
                image.close()

    def worker(self, url, output, wait_seconds, max_pages, crop):
        work_dir = Path.home() / "ComicPDF_Temp"
        work_dir.mkdir(exist_ok=True)
        for old in work_dir.glob("page_*.png"):
            try:
                old.unlink()
            except OSError:
                pass

        captured = []
        previous_hash = None

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    channel="msedge",
                    headless=False,
                    args=["--start-maximized"],
                )
                context = browser.new_context(
                    viewport={"width": 1740, "height": 862},
                    device_scale_factor=1,
                )
                page = context.new_page()
                page.goto(url, wait_until="domcontentloaded")

                self._continue_event.clear()
                self._continue_event.wait()

                for number in range(1, max_pages + 1):
                    raw = work_dir / "_raw.png"
                    final = work_dir / f"page_{number:04d}.png"

                    page.screenshot(path=str(raw), full_page=False)
                    self.crop_image(raw, final, crop)
                    raw.unlink(missing_ok=True)

                    current_hash = self.image_hash(final)
                    if current_hash == previous_hash:
                        final.unlink(missing_ok=True)
                        break

                    captured.append(final)
                    previous_hash = current_hash
                    self.update_status(f"已保存第 {number} 页，正在翻页……")

                    next_button = page.get_by_text("下一页", exact=True).last
                    if next_button.count() == 0 or not next_button.is_visible():
                        break

                    classes = (next_button.get_attribute("class") or "").lower()
                    if (
                        "disabled" in classes
                        or next_button.get_attribute("aria-disabled") == "true"
                        or next_button.get_attribute("disabled") is not None
                    ):
                        break

                    try:
                        next_button.click(timeout=5000)
                    except PlaywrightTimeoutError:
                        break

                    time.sleep(wait_seconds)

                browser.close()

            self.images_to_pdf(captured, output)
            self.finish(True, f"完成，共保存 {len(captured)} 页。\nPDF：{output}")

        except Exception as exc:
            self.finish(False, f"运行失败：{exc}")


if __name__ == "__main__":
    ComicPDFApp().mainloop()
