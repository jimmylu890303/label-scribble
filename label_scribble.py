import tkinter as tk
from tkinter import filedialog, simpledialog
import numpy as np
from PIL import Image, ImageTk
import cv2
import os

scribbles = [] 
current_class = 1 
image = None 
mask = None  
BORDER_WIDTH = 5
drawing = False  # 是否正在繪製
last_x, last_y = None, None  # 記錄上一點的座標

image_index = 0  # 當前顯示的圖像索引
image_list = []  # 保存加載的圖像文件路徑
folder_path = ''
clear_flag = False
save_flag = False   

def load_folder():
    global image_list, image_index, image, mask, canvas_img, folder_path
    folder_path = filedialog.askdirectory()
    if not folder_path:
        return

    image_list = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    if not image_list:
        print("No images found in the selected folder.")
        return
    image_index = 0  # 從第一張圖開始
    load_image_from_list()

def load_image_from_list():
    global image, mask, canvas_img, image_index, save_flag
    save_flag = False
    if not image_list:
        print("No images loaded.")
        return

    # Read Image
    filepath = image_list[image_index]
    image = cv2.imread(filepath)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) 
    mask_shape = image.shape[:2]

    # Show Src Image On Canvas
    display_image = Image.fromarray(image)
    canvas_img = ImageTk.PhotoImage(display_image)
    canvas.create_image(BORDER_WIDTH, BORDER_WIDTH, anchor=tk.NW, image=canvas_img)
    canvas.config(width=image.shape[1] + BORDER_WIDTH * 2, height=image.shape[0] + BORDER_WIDTH * 2)

    # Check Mask
    parent_dir = os.path.dirname(folder_path)
    mask_dir = os.path.join(parent_dir, "scribble_mask")
    mask_file_name = f"{os.path.splitext(os.path.basename(filepath))[0]}.png"
    mask_path = os.path.join(mask_dir, mask_file_name)
    # if mask exists
    global mask, clear_flag
    if os.path.exists(mask_path) and clear_flag == False:
        print(f"Loading mask from {mask_path}")
        mask = Image.open(mask_path)
        mask = np.asarray(mask)
        mask = mask.copy()
        mask[mask == 3] = 255
        mask[mask == 2] = 3
        mask[mask == 1] = 2
        mask[mask == 0] = 1
        draw_mask_on_canvas()
    # first time to init mask
    if mask is None:
        mask = np.zeros(mask_shape, dtype=np.uint8)
    # Update UI
    update_image_label()
    print(f"Loaded image {filepath} ({image_index + 1}/{len(image_list)})")
    clear_flag = False

def draw_mask_on_canvas():
    if mask is None:
        return

    # 快速將 mask 映射到一張 PIL 圖片
    mask_image = Image.fromarray(mask).convert("L")  # 單通道灰度圖
    mask_overlay = Image.new("RGBA", mask_image.size, (0, 0, 0, 0))  # 初始化為透明背景

    # 為每個 class_id 添加顏色
    for class_id, color in class_colors.items():
        if class_id == 0 :  # 跳過背景類別
            continue

        # 解析 HTML 顏色格式並加入不透明度
        rgba_color = tuple(int(color.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)) + (255,)  # 完全不透明
        color_layer = Image.new("RGBA", mask_image.size, rgba_color)

        # 建立掩膜區域
        mask_for_class = mask_image.point(lambda p: 255 if p == class_id else 0, mode="L")
        mask_overlay.paste(color_layer, (0, 0), mask_for_class)  # 將該類別的顏色貼到主圖層

    # 更新 Canvas 上的圖片
    global canvas_mask_image  # 確保物件被保存
    canvas_mask_image = ImageTk.PhotoImage(mask_overlay)
    canvas.create_image(BORDER_WIDTH, BORDER_WIDTH, anchor=tk.NW, image=canvas_mask_image)


import threading

def async_load_image():
    threading.Thread(target=load_image_from_list).start()

def next_image():
    global image_index, mask, save_flag
    if not image_list:
        print("No images loaded.")
        return
    if save_flag:
        save_mask()
    mask.fill(0)
    if image_index < len(image_list) - 1:
        image_index += 1
        async_load_image()
    else:
        print("This is the last image.")

def prev_image():
    global image_index, mask, save_flag
    if not image_list:
        print("No images loaded.")
        return
    if save_flag == True:
        save_mask()
    mask.fill(0)
    # 移動到上一張圖像
    if image_index > 0:
        image_index -= 1
        async_load_image()
    else:
        print("This is the first image.")

def jump_to_image():
    global image_index, save_flag
    if not image_list:
        print("No images loaded.")
        return

    if save_flag == True:
        save_mask()

    try:
        target_index = int(jump_entry.get()) - 1  # 用戶輸入的索引（1-based）
        if 0 <= target_index < len(image_list):
            image_index = target_index
            load_image_from_list()
        else:
            print("Invalid index. Please enter a valid image number.")
    except ValueError:
        print("Invalid input. Please enter a number.")

def update_image_label():
    image_label.config(text=f"Image {image_index + 1}/{len(image_list)}")

def save_mask():
    global mask, image_index, image_list, folder_path
    if mask is None:
        print("No mask to save.")
        return
    
    # 處理儲存路徑
    current_image_path = image_list[image_index]
    image_name = os.path.splitext(os.path.basename(current_image_path))[0]
    mask_file_name = f"{image_name}.png"
    parent_dir = os.path.dirname(folder_path)
    save_dir = os.path.join(parent_dir, "scribble_mask")
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    save_path = os.path.join(save_dir, mask_file_name)

    palette = [
    0, 0, 0,        # 索引 0 -> 黑色 (背景)
    128, 0, 0,      # 索引 1 -> 紅色 (正常組織)
    0, 128, 0,      # 索引 2 -> 綠色 (腫瘤組織)
    128, 64, 128    # 索引 3 -> 紫色 (忽略區域)
    ]

    # 更改儲存格式
    mask[mask == 0] = 255
    mask[mask == 1] = 0
    mask[mask == 2] = 1    
    mask[mask == 3] = 2
    mask_pil = Image.fromarray(mask.astype(np.uint8), mode='P')  # 轉為 PIL 調色盤模式
    mask_pil.putpalette(palette)  # 套用調色盤
    mask_pil.save(save_path, 'PNG')

    print(f"Mask saved to {save_path}")

def start_draw(event):
    global drawing, last_x, last_y, save_flag
    drawing = True
    save_flag = True
    last_x, last_y = event.x, event.y  # 記錄起始點

def stop_draw(event):
    global drawing, last_x, last_y
    drawing = False
    last_x, last_y = None, None  # 清除起始點

def draw_scribble(event):
    global scribbles, mask, drawing, class_colors, last_x, last_y
    if not drawing or image is None:
        return

    # 獲取當前點
    x, y = event.x, event.y

    # 確保上一點存在
    if last_x is not None and last_y is not None:
        # 在 Canvas 上繪製線段
        canvas.create_line(last_x, last_y, x, y, fill=class_colors.get(current_class, "black"), width=2)

        # 更新掩膜（補全線段）
        cv2.line(mask, (last_x - BORDER_WIDTH, last_y - BORDER_WIDTH), (x - BORDER_WIDTH, y - BORDER_WIDTH), current_class, thickness=2)

    # 記錄當前點作為下一次的上一點
    last_x, last_y = x, y

def clear_mask():
    global mask,clear_flag

    if mask is not None:
        mask.fill(0)
        clear_flag = True
    load_image_from_list()




def set_class():
    global current_class, class_colors
    # 提示用戶輸入類別編號
    new_class = simpledialog.askinteger("Set Class", "Enter class number:", minvalue=0)
    if new_class is None:
        return

    print(f"Switched to class {current_class} with color {class_colors[current_class]}")

def set_class_button(class_id):
    global current_class
    current_class = class_id
    print(f"Switched to class {current_class} with color {class_colors[current_class]}")

def handle_keypress(event):
    """
    根据键盘输入执行不同操作。
    """
    global current_class
    key = event.char  # 获取按键字符

    if key.isdigit():  # 切换类别
        class_id = int(key)
        if class_id in class_colors:
            current_class = class_id
            print(f"Switched to class {current_class} with color {class_colors[current_class]}")
    elif key == 's':  # 按 's' 保存掩膜
        save_mask()
    elif key == 'c':  # 按 'c' 清除掩膜
        clear_mask()
    elif key == 'w':
        next_image()
    elif key == 'q':
        prev_image()

# 初始化 Tkinter 主窗口
root = tk.Tk()
root.title("Scribble Annotation Tool")

# 創建界面部件
frame = tk.Frame(root)
frame.pack(side=tk.TOP, fill=tk.X)

btn_load = tk.Button(frame, text="Load Folder", command=load_folder)
btn_load.pack(side=tk.LEFT, padx=5, pady=5)

btn_save = tk.Button(frame, text="Save Mask", command=save_mask)
btn_save.pack(side=tk.LEFT, padx=5, pady=5)

btn_prev = tk.Button(frame, text="Previous Image", command=prev_image)
btn_prev.pack(side=tk.LEFT, padx=5, pady=5)

btn_next = tk.Button(frame, text="Next Image", command=next_image)
btn_next.pack(side=tk.LEFT, padx=5, pady=5)

btn_clear_mask = tk.Button(frame, text="Clear Mask", command=clear_mask)
btn_clear_mask.pack(side=tk.LEFT, padx=5, pady=5)

# 圖像跳轉功能
jump_frame = tk.Frame(root)
jump_frame.pack(side=tk.TOP, fill=tk.X, pady=5)

image_label = tk.Label(jump_frame, text="Image 0/0")
image_label.pack(side=tk.LEFT, padx=5)

jump_entry = tk.Entry(jump_frame, width=5)
jump_entry.pack(side=tk.LEFT, padx=5)

btn_jump = tk.Button(jump_frame, text="Jump to", command=jump_to_image)
btn_jump.pack(side=tk.LEFT, padx=5)

# 創建類別選擇按鈕

class_names = {
    1: "Background (1)",
    2: "Normal Tissue (2)",
    3: "Target Disease (3)",
}

class_colors = {
    1: "#000000",  # 白色
    2: "#FF0000",  # 紅色
    3: "#00FF00",  # 綠色
}

# 創建類別選擇按鈕
class_button_frame = tk.Frame(root)
class_button_frame.pack(side=tk.TOP, fill=tk.X, pady=5)

for class_id in range(len(class_names)):
    class_id+=1
    color = class_colors[class_id]
    name = class_names[class_id]
    btn = tk.Button(
        class_button_frame,
        text=name,
        bg='#0070C0', 
        fg='white',
        command=lambda c=class_id: set_class_button(c)  # 設定按鈕動作
    )
    btn.pack(side=tk.LEFT, padx=2, pady=2)

root.bind("<KeyPress>", handle_keypress)

canvas = tk.Canvas(root, bg="white")
canvas.pack(fill=tk.BOTH, expand=True)

canvas.bind("<ButtonPress-1>", start_draw)  # 開始繪製
canvas.bind("<B1-Motion>", draw_scribble)  # 畫塗鴉
canvas.bind("<ButtonRelease-1>", stop_draw)  # 停止繪製

# 啟動主循環
root.mainloop()