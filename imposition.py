import math
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, portrait
from pypdf import PdfReader, PdfWriter, PageObject, Transformation
from reportlab.lib.units import mm

class Imposer:
    def __init__(self, input_pdf_stream, pages_per_sheet_n):
        """
        Initialize the Imposer.
        :param input_pdf_stream: File-like object or path to input PDF.
        :param pages_per_sheet_n: Integer, number of pages per physical sheet side (N-up).
        """
        self.reader = PdfReader(input_pdf_stream)
        self.total_input_pages = len(self.reader.pages)
        self.n_up = pages_per_sheet_n
        
        # CHANGED: Use A4 Portrait (210mm x 297mm)
        self.sheet_width, self.sheet_height = portrait(A4)
        
        # Calculate grid dimensions (cols x rows)
        self.cols, self.rows = self.calculate_grid(self.n_up)
        
    def calculate_grid(self, n):
        """
        Calculate the best grid (cols, rows) for N pages on A4 Portrait.
        Finds a grid such that cols * rows >= n.
        Prioritizes:
        1. Minimal waste (cols * rows - n)
        2. Portrait shape (rows >= cols) to match A4.
        """
        best_rows = n
        best_cols = 1
        min_waste = float('inf')
        
        # Heuristic: Iterate cols from 1 up to sqrt(n) + something
        # For N=5, sqrt=2.2. Cols to check: 1, 2.
        # Col 1: Rows 5. Cap=5. Waste=0.
        # Col 2: Rows 3. Cap=6. Waste=1.
        
        # We want to check reasonably up to n.
        limit = int(math.ceil(math.sqrt(n))) + 2
        
        candidates = []
        
        for c in range(1, limit + 1):
            r = math.ceil(n / c)
            capacity = r * c
            waste = capacity - n
            
            # Penalize wide layouts on portrait sheet
            # Ratio of sheet is ~1.41 (H/W)
            # We prefer R/C close to 1.41
            # Or just prefer R >= C
            
            candidates.append((c, r, waste))

        # Sort candidates
        # New Heuristic: minimize (Waste + AspectRatioDiff)
        # This allows small waste (e.g. 1 page) if it provides much better shape (e.g. 2x3 vs 1x5).
        
        target_ratio = 1.414
        
        candidates.sort(key=lambda x: x[2] + abs((x[1]/x[0]) - target_ratio))
        
        best = candidates[0]
        return best[0], best[1]

    def generate(self):
        """
        Generate the imposed PDF.
        Returns a BytesIO object containing the PDF.
        """
        sheets_per_stack = math.ceil(self.total_input_pages / (2 * self.n_up))
        
        output_writer = PdfWriter()
        
        # Calculate cell dimensions
        # We want "no much gap", just "small gap with line of separation"
        # Let's define specific margin/gap if needed, or just full bleed with lines.
        # User said "filled and no much gap between the pages just a small gap with line of separation".
        # We will assume the visible cut lines are drawn ON TOP of the pages or in the gutter.
        # Let's reserve a tiny gutter for the line? 
        # Or just draw the line at the boundary.
        
        cell_width = self.sheet_width / self.cols
        cell_height = self.sheet_height / self.rows
        
        # Generate Sheets
        for sheet_idx in range(sheets_per_stack):
            # Create Front Side
            front_page = PageObject.create_blank_page(width=self.sheet_width, height=self.sheet_height)
            self._fill_sheet_side(front_page, sheet_idx, sheets_per_stack, is_front=True, 
                                  cell_width=cell_width, cell_height=cell_height)
            self._draw_overlay(front_page, cell_width, cell_height, sheet_idx, True)
            output_writer.add_page(front_page)
            
            # Create Back Side
            back_page = PageObject.create_blank_page(width=self.sheet_width, height=self.sheet_height)
            self._fill_sheet_side(back_page, sheet_idx, sheets_per_stack, is_front=False,
                                  cell_width=cell_width, cell_height=cell_height)
             # Cut lines on back too
            self._draw_overlay(back_page, cell_width, cell_height, sheet_idx, False)
            output_writer.add_page(back_page)
            
        output_stream = io.BytesIO()
        output_writer.write(output_stream)
        output_stream.seek(0)
        return output_stream

    def _draw_overlay(self, page_obj, cell_width, cell_height, sheet_idx, is_front):
        """
        Draws cut lines and page numbers on a temporary PDF page and merges it.
        """
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(self.sheet_width, self.sheet_height))
        
        # 1. Draw Cut Lines
        can.setStrokeColorRGB(0.5, 0.5, 0.5) 
        can.setLineWidth(0.5)
        can.setDash([2, 2])
        
        # Vertical
        for c in range(1, self.cols):
            x = c * cell_width
            can.line(x, 0, x, self.sheet_height)
        # Horizontal
        for r in range(1, self.rows):
            y = r * cell_height
            can.line(0, y, self.sheet_width, y)
            
        # 2. Draw Page Numbers
        can.setFillColorRGB(0, 0, 0)
        can.setFont("Helvetica-Bold", 5)
        
        # Reset dash for text background box?
        # Actually just draw text with a small white background retangle for visibility?
        # Or just black text. Let's start with just text, maybe add a small white box behind it.
        
        for row in range(self.rows):
            for col in range(self.cols):
                stack_index = row * self.cols + col
                global_pair_index = (sheet_idx * self.n_up) + stack_index
                
                if is_front:
                    page_num = (global_pair_index * 2) + 1
                else:
                    page_num = (global_pair_index * 2) + 2
                
                # Check bounds
                if page_num > self.total_input_pages:
                    continue
                    
                # Calculate Position
                target_col = col
                if not is_front:
                    target_col = self.cols - 1 - col
                
                # Top-Left of the cell
                cell_x = target_col * cell_width
                cell_y = self.sheet_height - (row * cell_height) # Top Y of cell
                
                # Draw Text
                text = f"{page_num}"
                text_x = cell_x + 10  # Moved away from corner
                text_y = cell_y - 14 # Moved down from top
                
                # Optional: White background rect for readability
                can.setFillColorRGB(1, 1, 1) # White
                text_width = can.stringWidth(text, "Helvetica-Bold", 5)
                can.rect(text_x - 2, text_y - 2, text_width + 4, 8, fill=1, stroke=0)
                
                can.setFillColorRGB(0, 0, 0) # Black
                can.drawString(text_x, text_y, text)

        can.save()
        packet.seek(0)
        
        overlay_pdf = PdfReader(packet)
        page_obj.merge_page(overlay_pdf.pages[0])

    def _fill_sheet_side(self, canvas_page, sheet_idx, sheets_per_stack, is_front, cell_width, cell_height):
        """
        Places the correct source pages onto the canvas_page (PyPDF PageObject).
        """
        # Iterate through the N grid positions (stacks)
        for row in range(self.rows):
            for col in range(self.cols):
                # Calculate stack index k (0 to N-1)
                # Order: Typically Left-to-Right, Top-to-Bottom
                stack_index = row * self.cols + col
                
                # SEQUENTIAL N-UP LOGIC (User Request)
                # Sheet 0 (Front) contains pairs 0, 1, 2... N-1
                # Sheet 1 (Front) contains pairs N, N+1... 2N-1
                
                # Global pair index across all sheets
                global_pair_index = (sheet_idx * self.n_up) + stack_index
                
                if is_front:
                    # Odd pages: 1, 3, 5... (1-based)
                    # Pair 0 -> Page 1
                    # Pair 1 -> Page 3
                    current_page_num_1base = (global_pair_index * 2) + 1
                else:
                    # Even pages: 2, 4, 6... (1-based)
                    # Pair 0 -> Page 2
                    # Pair 1 -> Page 4
                    current_page_num_1base = (global_pair_index * 2) + 2
                
                # Check if this page exists in input
                if current_page_num_1base <= self.total_input_pages:
                    source_page = self.reader.pages[current_page_num_1base - 1]
                    
                    # Transformation Matrix Calculation
                    mb = source_page.mediabox
                    src_w = float(mb.width)
                    src_h = float(mb.height)
                    
                    # User requested to minimize wasted space and match tightly packed reference images.
                    # Setting padding_factor to 1.0 means the source page determines its own margins.
                    padding_factor = 1.0 
                    
                    avail_w = cell_width * padding_factor
                    avail_h = cell_height * padding_factor
                    
                    scale_w = avail_w / src_w
                    scale_h = avail_h / src_h
                    scale = min(scale_w, scale_h) # Uniform scaling
                    
                    # Center in cell
                    scaled_src_w = src_w * scale
                    scaled_src_h = src_h * scale
                    
                    off_x_in_cell = (cell_width - scaled_src_w) / 2
                    off_y_in_cell = (cell_height - scaled_src_h) / 2
                    
                    # Cell Position on Sheet
                    # Y is typically bottom-up in PDF. 
                    # Row 0 is Top.
                    
                    target_col = col
                    target_row = row
                    
                    if not is_front:
                        # BACK SIDE MIRRORING (Horizontal flip of the GRID column index)
                        target_col = self.cols - 1 - col
                                            
                    # Calculate final coordinates (bottom-left corner of the placed page)
                    cell_x_global = target_col * cell_width
                    cell_y_global = self.sheet_height - (target_row + 1) * cell_height
                    
                    final_x = cell_x_global + off_x_in_cell
                    final_y = cell_y_global + off_y_in_cell
                    
                    op = Transformation().scale(scale, scale).translate(final_x, final_y)
                    canvas_page.merge_transformed_page(source_page, op)

