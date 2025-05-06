import os
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageDraw
import pandas as pd

# === Configure paths ===
input_folder = r"C:"
output_folder = r"C:"

image_extensions = [".jpg", ".jpeg", ".png", ".tif", ".bmp"]
all_files = sorted([f for f in os.listdir(input_folder) if os.path.splitext(f)[1].lower() in image_extensions])

annotations = []

class CombinedAnnotationTool:
    def __init__(self, master):
        self.master = master
        self.master.title("CPE/No CPE Annotator")

        self.canvas = tk.Canvas(master, cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.btn_frame = tk.Frame(master)
        self.btn_frame.pack(pady=10)

        self.prev_btn = tk.Button(self.btn_frame, text="Previous Image", command=self.prev_image)
        self.prev_btn.pack(side=tk.LEFT, padx=5)

        self.cpe_btn = tk.Button(self.btn_frame, text="CPE", width=15, height=2, command=self.mark_cpe)
        self.cpe_btn.pack(side=tk.LEFT, padx=5)

        self.no_cpe_btn = tk.Button(self.btn_frame, text="No CPE", width=15, height=2, command=self.mark_no_cpe)
        self.no_cpe_btn.pack(side=tk.LEFT, padx=5)

        self.undo_btn = tk.Button(self.btn_frame, text="Undo Box", command=self.undo_last_box)
        self.undo_btn.pack(side=tk.LEFT, padx=5)

        self.next_btn = tk.Button(self.btn_frame, text="Next Image", command=self.next_image)
        self.next_btn.pack(side=tk.LEFT, padx=5)

        self.image_index = 0
        self.start_x = self.start_y = None
        self.rect = None
        self.tk_img = None
        self.current_class = None
        self.bboxes = []
        self.filename = ""
        self.history = {}

        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        self.load_image()

    def load_image(self):
        if self.image_index < 0:
            self.image_index = 0
        elif self.image_index >= len(all_files):
            self.save_annotations()
            messagebox.showinfo("Done", "✅ All images annotated.")
            self.master.quit()
            return

        self.filename = all_files[self.image_index]
        self.image_path = os.path.join(input_folder, self.filename)
        self.image = Image.open(self.image_path).convert("RGB")

        self.tk_img = ImageTk.PhotoImage(self.image)
        self.canvas.config(width=self.tk_img.width(), height=self.tk_img.height())
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)

        self.bboxes = []
        self.current_class = None
        self.update_button_colors()
        self.enable_class_buttons()

    def mark_cpe(self):
        if self.current_class is not None:
            return

        self.current_class = "CPE"
        self.bboxes.clear()
        self.canvas.delete("all")
        self.tk_img = ImageTk.PhotoImage(self.image)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)
        self.update_button_colors()
        self.disable_class_buttons()

    def mark_no_cpe(self):
        if self.current_class is not None:
            return

        self.current_class = "No CPE"
        self.bboxes.clear()
        self.update_button_colors()
        self.disable_class_buttons()

    def update_button_colors(self):
        if self.current_class == "CPE":
            self.cpe_btn.config(bg="green")
            self.no_cpe_btn.config(bg="SystemButtonFace")
        elif self.current_class == "No CPE":
            self.no_cpe_btn.config(bg="red")
            self.cpe_btn.config(bg="SystemButtonFace")
        else:
            self.no_cpe_btn.config(bg="SystemButtonFace")
            self.cpe_btn.config(bg="SystemButtonFace")

    def disable_class_buttons(self):
        self.cpe_btn.config(state=tk.DISABLED)
        self.no_cpe_btn.config(state=tk.DISABLED)

    def enable_class_buttons(self):
        self.cpe_btn.config(state=tk.NORMAL)
        self.no_cpe_btn.config(state=tk.NORMAL)

    def on_click(self, event):
        if self.current_class != "CPE":
            return
        self.start_x = event.x
        self.start_y = event.y
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, event.x, event.y,
            outline="red", width=3
        )

    def on_drag(self, event):
        if self.current_class != "CPE" or self.rect is None:
            return
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        if self.current_class != "CPE" or self.rect is None:
            return
        end_x, end_y = event.x, event.y
        x1, y1 = min(self.start_x, end_x), min(self.start_y, end_y)
        x2, y2 = max(self.start_x, end_x), max(self.start_y, end_y)

        self.bboxes.append({
            "x1": x1, "y1": y1, "x2": x2, "y2": y2
        })
        self.rect = None

    def undo_last_box(self):
        if self.bboxes:
            self.bboxes.pop()
            self.canvas.delete("all")
            self.tk_img = ImageTk.PhotoImage(self.image)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)
            for box in self.bboxes:
                self.canvas.create_rectangle(box["x1"], box["y1"], box["x2"], box["y2"], outline="red", width=3)

    def next_image(self):
        if self.current_class is None:
            messagebox.showwarning("Hinweis", "Bitte zuerst 'CPE' oder 'No CPE' auswählen.")
            return

        self.history[self.filename] = {
            "class": self.current_class,
            "bboxes": self.bboxes.copy()
        }

        if self.current_class == "No CPE":
            annotations.append({"filename": self.filename, "class": "No CPE"})
        elif self.current_class == "CPE":
            for box in self.bboxes:
                annotations.append({
                    "filename": self.filename,
                    "class": "CPE",
                    "x1": box["x1"],
                    "y1": box["y1"],
                    "x2": box["x2"],
                    "y2": box["y2"]
                })
            img_copy = self.image.copy()
            draw = ImageDraw.Draw(img_copy)
            for box in self.bboxes:
                draw.rectangle([box["x1"], box["y1"], box["x2"], box["y2"]], outline="red", width=3)
            img_copy.save(os.path.join(output_folder, self.filename))

        annotations.append({})  # Leerzeile

        self.image_index += 1
        self.load_image()

    def prev_image(self):
        if self.image_index > 0:
            self.image_index -= 1
            self.load_image()

    def save_annotations(self):
        if annotations:
            df = pd.DataFrame(annotations)
            excel_path = os.path.join(output_folder, "bounding_boxes.xlsx")
            df.to_excel(excel_path, index=False)
            print(f"📄 Excel saved to: {excel_path}")

# Starte Tool
root = tk.Tk()
app = CombinedAnnotationTool(root)
root.mainloop()
