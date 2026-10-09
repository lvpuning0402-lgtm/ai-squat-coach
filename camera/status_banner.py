"""Camera text that adapts to the brightness directly behind it."""
import cv2


def text_color(frame, text, x, y, scale, thickness=1):
    """Sample the visible text area before drawing; return one foreground color."""
    (width, height), baseline = cv2.getTextSize(
        text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
    rows, cols = frame.shape[:2]
    left, right = max(0, x), min(cols, x + width + 1)
    top, bottom = max(0, y - height), min(rows, y + baseline + 1)
    brightness = 0
    if left < right and top < bottom:
        region = frame[top:bottom, left:right]
        brightness = cv2.mean(cv2.cvtColor(region, cv2.COLOR_BGR2GRAY))[0]
    return (0, 0, 0) if brightness >= 145 else (255, 255, 255)


def draw_adaptive_text(frame, text, x, y, scale=.47, thickness=1):
    text = str(text)
    if not text:
        return
    ink = text_color(frame, text, x, y, scale, thickness)
    cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                scale, ink, thickness, cv2.LINE_AA)


def draw_status_banner(frame, message, bottom=34):
    height, width = frame.shape[:2]
    message = str(message)
    scale = .52
    (text_width, _), _ = cv2.getTextSize(message, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
    if text_width > max(1, width - 32):
        scale *= max(1, width - 32) / text_width
    (_, text_height), _ = cv2.getTextSize(message, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
    y = max(text_height + 16, height - bottom)
    draw_adaptive_text(frame, message, 16, y, scale=scale)
