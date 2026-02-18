from PIL import Image, ImageDraw
import math

def create_gradient_background(size, start_color, end_color):
    """Создает градиентный фон от светлого к темному."""
    img = Image.new("RGB", (size, size))
    pixels = img.load()
    
    for y in range(size):
        # Вычисляем коэффициент для градиента (0.0 вверху, 1.0 внизу)
        ratio = y / size
        # Интерполируем цвет
        r = int(start_color[0] * (1 - ratio) + end_color[0] * ratio)
        g = int(start_color[1] * (1 - ratio) + end_color[1] * ratio)
        b = int(start_color[2] * (1 - ratio) + end_color[2] * ratio)
        
        for x in range(size):
            pixels[x, y] = (r, g, b)
    
    return img

def draw_squircle_mask(size, radius_ratio=0.2):
    """Создает маску для скругленных углов (squircle форма)."""
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    
    # Радиус скругления (20% от размера)
    radius = int(size * radius_ratio)
    
    # Рисуем скругленный квадрат
    draw.rounded_rectangle(
        [(0, 0), (size - 1, size - 1)],
        radius=radius,
        fill=255
    )
    
    return mask

def draw_geometric_ai(draw, center_x, center_y, size, line_thickness):
    """Рисует буквы 'AI' в геометрическом стиле."""
    white_color = (255, 255, 255)
    
    # Размер букв (60-70% от размера иконки)
    letter_size = int(size * 0.65)
    letter_spacing = int(size * 0.08)
    
    # Позиция начала буквы A (центрируем обе буквы как единое целое)
    total_width = letter_size + letter_spacing + letter_size // 3
    start_x = center_x - total_width // 2
    start_y = center_y - letter_size // 2
    
    # === БУКВА "A" ===
    # Левая диагональ A (от нижнего левого угла к верхней точке)
    a_left_bottom = (start_x, start_y + letter_size)
    a_left_top = (start_x + letter_size // 3, start_y)
    
    # Правая диагональ A (от верхней точки к нижнему правому углу)
    a_right_top = (start_x + letter_size // 3, start_y)
    a_right_bottom = (start_x + letter_size * 2 // 3, start_y + letter_size)
    
    # Горизонтальная перекладина A (посередине)
    a_bar_y = start_y + letter_size // 2
    a_bar_left = (start_x + letter_size // 6, a_bar_y)
    a_bar_right = (start_x + letter_size // 2, a_bar_y)
    
    # Рисуем букву A
    draw.line([a_left_bottom, a_left_top], fill=white_color, width=line_thickness)
    draw.line([a_right_top, a_right_bottom], fill=white_color, width=line_thickness)
    draw.line([a_bar_left, a_bar_right], fill=white_color, width=line_thickness)
    
    # === БУКВА "I" ===
    i_start_x = start_x + letter_size + letter_spacing
    i_center_x = i_start_x + letter_size // 6
    
    # Вертикальная линия I
    i_top = (i_center_x, start_y)
    i_bottom = (i_center_x, start_y + letter_size)
    draw.line([i_top, i_bottom], fill=white_color, width=line_thickness)
    
    # Верхняя горизонтальная линия I
    i_top_line_left = (i_start_x, start_y)
    i_top_line_right = (i_start_x + letter_size // 3, start_y)
    draw.line([i_top_line_left, i_top_line_right], fill=white_color, width=line_thickness)
    
    # Нижняя горизонтальная линия I
    i_bottom_line_left = (i_start_x, start_y + letter_size)
    i_bottom_line_right = (i_start_x + letter_size // 3, start_y + letter_size)
    draw.line([i_bottom_line_left, i_bottom_line_right], fill=white_color, width=line_thickness)

def draw_icon(size):
    """Рисует иконку: темно-синий градиентный фон, темно-красный круг, белые буквы AI."""
    # Цвета
    bg_start = (25, 25, 112)  # Светлый темно-синий (вверху)
    bg_end = (8, 8, 40)       # Темный темно-синий (внизу)
    circle_color = (100, 0, 20)  # Темно-красный цвет гнилой вишни
    white_color = (255, 255, 255)
    
    # Создаем градиентный фон
    img = create_gradient_background(size, bg_start, bg_end)
    draw = ImageDraw.Draw(img)
    
    # Координаты центра
    center_x = size // 2
    center_y = size // 2
    
    # Размер круга (занимает примерно 80% размера иконки)
    circle_radius = int(size * 0.4)
    
    # Рисуем круг
    circle_bbox = [
        center_x - circle_radius,
        center_y - circle_radius,
        center_x + circle_radius,
        center_y + circle_radius
    ]
    draw.ellipse(circle_bbox, fill=circle_color, outline=None)
    
    # Толщина линий для букв (пропорциональна размеру)
    line_thickness = max(2, int(size * 0.06))
    
    # Рисуем буквы "AI" внутри круга
    draw_geometric_ai(draw, center_x, center_y, size, line_thickness)
    
    # Применяем скругление углов (squircle форма)
    mask = draw_squircle_mask(size, radius_ratio=0.15)
    img.putalpha(mask)
    
    # Конвертируем обратно в RGB для ICO формата
    if img.mode == "RGBA":
        # Создаем белый фон для прозрачных областей
        rgb_img = Image.new("RGB", img.size, bg_end)
        rgb_img.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
        return rgb_img
    
    return img

# Размеры иконки для Windows ICO
sizes = [256, 128, 64, 48, 32, 16]
icons = []

print("Создание иконки приложения...")
print("   Дизайн: темно-синий градиентный фон, темно-красный круг, белые буквы AI")
print("   Размеры:", ", ".join([f"{s}x{s}" for s in sizes]))

for size in sizes:
    icon = draw_icon(size)
    # Убеждаемся, что изображение в RGB режиме
    if icon.mode != "RGB":
        icon = icon.convert("RGB")
    icons.append(icon)

# Сохранение в формате ICO
try:
    icons[0].save(
        "app.ico",
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=icons[1:]
    )
    print("OK: Иконка 'app.ico' успешно создана!")
    print(f"   Создано {len(sizes)} размеров: {', '.join([f'{s}x{s}' for s in sizes])}")
except Exception as e:
    print(f"ОШИБКА при сохранении: {e}")
    # Альтернативный способ - сохранить только один размер
    print("Попытка альтернативного метода сохранения...")
    try:
        icons[0].save("app.ico", format="ICO")
        print("OK: Иконка 'app.ico' создана (только размер 256x256)")
    except Exception as e2:
        print(f"КРИТИЧЕСКАЯ ОШИБКА: {e2}")
