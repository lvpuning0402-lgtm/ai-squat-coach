"""Readable camera status text over light and dark backgrounds."""
import cv2


def draw_status_banner(frame, message, bottom=34):
    height, width = frame.shape[:2]
    scale = min(.52, max(.3, (width - 48) / max(len(message) * 11, 1)))
    (text_width, text_height), baseline = cv2.getTextSize(message, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
    y = max(text_height + 16, height - bottom)
    cv2.rectangle(frame, (8, y - text_height - 10),
                  (min(width - 8, text_width + 28), min(height - 1, y + baseline + 8)), (22, 28, 32), -1)
    cv2.putText(frame, message, (16, y), cv2.FONT_HERSHEY_SIMPLEX,
                scale, (255, 255, 255), 1, cv2.LINE_AA)
