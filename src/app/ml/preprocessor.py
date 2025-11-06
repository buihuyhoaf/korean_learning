"""
Preprocessor for converting stroke data to 28x28 grayscale images
Normalizes and rasterizes stroke points for CNN input
"""
import numpy as np
from typing import List, Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Image dimensions for CNN input
IMAGE_SIZE = 28
IMAGE_SCALE = 1.0  # Scale factor for image


class StrokePreprocessor:
    """Preprocessor for converting stroke data to CNN input format"""
    
    def __init__(self, image_size: int = IMAGE_SIZE):
        """
        Initialize preprocessor.
        
        Args:
            image_size: Target image size (default 28x28)
        """
        self.image_size = image_size
    
    def preprocess(self, strokes: List[Dict[str, Any]]) -> np.ndarray:
        """
        Preprocess stroke data into normalized 28x28 grayscale image.
        
        Args:
            strokes: List of stroke dictionaries with format:
                [
                    {
                        "stroke_id": int,
                        "points": [[x, y], [x, y], ...],
                        "timestamp": int (optional)
                    },
                    ...
                ]
        
        Returns:
            28x28 grayscale image array (normalized 0-1)
        
        Raises:
            ValueError: If stroke data is invalid
        """
        if not strokes:
            raise ValueError("Stroke data cannot be empty")
        
        # Flatten all points from all strokes
        all_points = []
        for stroke in strokes:
            points = stroke.get("points", [])
            if not points:
                continue
            
            for point in points:
                if len(point) < 2:
                    raise ValueError(f"Invalid point format: {point}")
                all_points.append([float(point[0]), float(point[1])])
        
        if not all_points:
            raise ValueError("No valid points found in strokes")
        
        # Convert to numpy array
        points_array = np.array(all_points, dtype=np.float32)
        
        # Normalize coordinates
        normalized_points = self._normalize_points(points_array)
        
        # Rasterize to image
        image = self._rasterize_strokes(normalized_points, strokes)
        
        return image
    
    def _normalize_points(self, points: np.ndarray) -> np.ndarray:
        """
        Normalize points to fit in [0, IMAGE_SIZE] range.
        Preserves aspect ratio and centers the drawing.
        
        Args:
            points: Array of (x, y) points
            
        Returns:
            Normalized points array
        """
        if points.shape[0] == 0:
            return points
        
        # Get bounding box
        min_x, min_y = points.min(axis=0)
        max_x, max_y = points.max(axis=0)
        
        width = max_x - min_x
        height = max_y - min_y
        
        # Handle edge case: single point or zero-size drawing
        if width == 0:
            width = 1.0
        if height == 0:
            height = 1.0
        
        # Calculate scale to fit in image with padding
        padding = 0.1  # 10% padding
        scale = min(
            (self.image_size * (1 - 2 * padding)) / width,
            (self.image_size * (1 - 2 * padding)) / height
        )
        
        # Center and scale
        center_x = (min_x + max_x) / 2.0
        center_y = (min_y + max_y) / 2.0
        
        normalized = points.copy()
        normalized[:, 0] = (normalized[:, 0] - center_x) * scale + self.image_size / 2.0
        normalized[:, 1] = (normalized[:, 1] - center_y) * scale + self.image_size / 2.0
        
        # Clamp to image bounds
        normalized[:, 0] = np.clip(normalized[:, 0], 0, self.image_size - 1)
        normalized[:, 1] = np.clip(normalized[:, 1], 0, self.image_size - 1)
        
        return normalized
    
    def _rasterize_strokes(
        self, 
        normalized_points: np.ndarray, 
        strokes: List[Dict[str, Any]]
    ) -> np.ndarray:
        """
        Rasterize normalized stroke points into a grayscale image.
        Draws strokes as lines with anti-aliasing.
        
        Args:
            normalized_points: Normalized point coordinates
            strokes: Original stroke data for drawing individual strokes
            
        Returns:
            28x28 grayscale image (0-1 range)
        """
        # Initialize image
        image = np.zeros((self.image_size, self.image_size), dtype=np.float32)
        
        # Draw each stroke
        point_idx = 0
        for stroke in strokes:
            points = stroke.get("points", [])
            if len(points) < 2:
                continue
            
            # Draw lines between consecutive points in this stroke
            for i in range(len(points) - 1):
                if point_idx + i + 1 >= len(normalized_points):
                    break
                
                p1 = normalized_points[point_idx + i]
                p2 = normalized_points[point_idx + i + 1]
                
                # Draw line using Bresenham-like algorithm with anti-aliasing
                self._draw_line(image, p1, p2, stroke_width=2.0)
            
            point_idx += len(points)
        
        # Normalize to 0-1 range
        if image.max() > 0:
            image = image / image.max()
        
        return image
    
    def _draw_line(
        self, 
        image: np.ndarray, 
        p1: np.ndarray, 
        p2: np.ndarray, 
        stroke_width: float = 2.0
    ):
        """
        Draw a line between two points with anti-aliasing.
        
        Args:
            image: Image array to draw on
            p1: Start point (x, y)
            p2: End point (x, y)
            stroke_width: Width of the stroke
        """
        x1, y1 = int(p1[0]), int(p1[1])
        x2, y2 = int(p2[0]), int(p2[1])
        
        # Simple line drawing with stroke width
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy
        
        x, y = x1, y1
        
        # Draw pixels along the line
        while True:
            # Draw pixel with anti-aliasing (stroke width)
            for offset_x in range(-int(stroke_width), int(stroke_width) + 1):
                for offset_y in range(-int(stroke_width), int(stroke_width) + 1):
                    px, py = x + offset_x, y + offset_y
                    if 0 <= px < self.image_size and 0 <= py < self.image_size:
                        # Distance-based intensity for anti-aliasing
                        dist = np.sqrt(offset_x**2 + offset_y**2)
                        if dist <= stroke_width:
                            intensity = 1.0 - (dist / stroke_width) * 0.5
                            image[py, px] = max(image[py, px], intensity)
            
            if x == x2 and y == y2:
                break
            
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
    
    def preprocess_batch(self, batch_strokes: List[List[Dict[str, Any]]]) -> np.ndarray:
        """
        Preprocess a batch of stroke data.
        
        Args:
            batch_strokes: List of stroke data lists
            
        Returns:
            Batch of images shape (batch_size, 28, 28, 1)
        """
        images = []
        for strokes in batch_strokes:
            image = self.preprocess(strokes)
            images.append(image)
        
        # Stack and add channel dimension
        batch = np.stack(images, axis=0)
        batch = np.expand_dims(batch, axis=-1)  # Add channel dimension
        
        return batch


def unicode_to_char(unicode_code: int) -> str:
    """
    Convert Unicode code point to Hangul character.
    Hangul range: 0xAC00 (가) to 0xD7A3 (힣)
    
    Args:
        unicode_code: Unicode code point (0-2349 for Hangul)
        
    Returns:
        Hangul character string
    """
    # Hangul starts at 0xAC00
    hangul_start = 0xAC00
    if 0 <= unicode_code < 2350:
        return chr(hangul_start + unicode_code)
    return "?"

