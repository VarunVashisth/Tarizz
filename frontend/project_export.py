"""
project_export.py - Export entire project to PDF
=================================================
Exports a complete project with:
- Tree hierarchy structure
- All subpage content with formatting
- Flowcharts as PNG images
- Professional PDF layout
"""

import os
import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, PageBreak,
                               Image, Table, TableStyle, HRFlowable, Preformatted,
                               KeepTogether)
from reportlab.lib import colors
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage
import tkinter as tk
from tkinter import filedialog, messagebox
from urllib.parse import unquote


class ProjectExporter:
    """Handles exporting a project to PDF"""
    
    def __init__(self, project_id, project_title, db_module):
        self.project_id = project_id
        self.project_title = project_title
        self.db = db_module
        self.temp_images = []  # Track temp files for cleanup
        self._pdf_font_cache = {}
        
    def export_to_pdf(self, output_path=None):
        """
        Export the entire project to PDF
        
        Args:
            output_path: Path to save PDF. If None, prompts user.
        
        Returns:
            True if successful, False otherwise
        """
        if not output_path:
            output_path = filedialog.asksaveasfilename(
                defaultextension='.pdf',
                filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
                initialfile=f"{self.project_title}.pdf"
            )
            if not output_path:
                return False
        
        try:
            # Create PDF document
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=0.75*inch,
                leftMargin=0.75*inch,
                topMargin=0.75*inch,
                bottomMargin=0.75*inch
            )
            
            # Build content
            story = []
            styles = self._create_styles()
            
            # Title page
            story.extend(self._create_title_page(styles))
            story.append(PageBreak())
            
            # Table of contents
            toc_items = self._build_toc()
            story.extend(self._create_toc(toc_items, styles))
            story.append(PageBreak())
            
            # Content sections
            story.extend(self._create_content(toc_items, styles))
            
            # Build PDF
            doc.build(story, onFirstPage=self._draw_page, onLaterPages=self._draw_page)
            
            # Cleanup temp files
            self._cleanup_temp_files()
            
            messagebox.showinfo(
                "Export Complete",
                f"Project exported successfully to:\n{output_path}"
            )
            return True
            
        except Exception as e:
            messagebox.showerror("Export Failed", f"Error exporting project:\n{str(e)}")
            self._cleanup_temp_files()
            return False
    
    def _create_styles(self):
        """Create custom paragraph styles for the PDF"""
        styles = getSampleStyleSheet()
        
        # Title style
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Title'],
            fontSize=28,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=12,
            alignment=TA_CENTER
        ))

        styles.add(ParagraphStyle(
            name='SectionLabel', parent=styles['Normal'], fontSize=8,
            leading=10, textColor=colors.HexColor('#64748b'),
            uppercase=True, spaceBefore=8, spaceAfter=6,
        ))
        styles.add(ParagraphStyle(
            name='CodeBlock', parent=styles['Code'], fontName='Courier',
            fontSize=8.5, leading=12, textColor=colors.HexColor('#e2e8f0'),
            backColor=colors.HexColor('#0f172a'), borderColor=colors.HexColor('#334155'),
            borderWidth=0.5, borderPadding=10, leftIndent=8, rightIndent=8,
            spaceBefore=7, spaceAfter=9,
        ))
        styles.add(ParagraphStyle(
            name='ImageMarker', parent=styles['Code'], fontSize=9,
            textColor=colors.HexColor('#2563eb'), backColor=colors.HexColor('#eff6ff'),
            borderPadding=5, spaceBefore=4, spaceAfter=4,
        ))
        styles.add(ParagraphStyle(
            name='Caption', parent=styles['Normal'], fontSize=8.5, leading=11,
            textColor=colors.HexColor('#64748b'), alignment=TA_CENTER,
            spaceBefore=4, spaceAfter=12,
        ))
        
        # Heading 1
        styles.add(ParagraphStyle(
            name='CustomHeading1',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            spaceBefore=12
        ))
        
        # Heading 2
        styles.add(ParagraphStyle(
            name='CustomHeading2',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=8,
            spaceBefore=8,
            leftIndent=20
        ))
        
        # Heading 3
        styles.add(ParagraphStyle(
            name='CustomHeading3',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#7f8c8d'),
            spaceAfter=6,
            spaceBefore=6,
            leftIndent=40
        ))
        
        # Body text
        styles.add(ParagraphStyle(
            name='CustomBody',
            parent=styles['BodyText'],
            fontSize=11,
            alignment=TA_JUSTIFY,
            spaceAfter=6
        ))
        
        return styles

    def _draw_page(self, canvas, doc):
        """Add restrained documentation-style header, footer and page number."""
        canvas.saveState()
        width, height = A4
        if doc.page > 1:
            canvas.setStrokeColor(colors.HexColor('#e2e8f0'))
            canvas.line(doc.leftMargin, height - 38, width - doc.rightMargin, height - 38)
            canvas.setFont('Helvetica', 8)
            canvas.setFillColor(colors.HexColor('#64748b'))
            canvas.drawString(doc.leftMargin, height - 29, self.project_title[:70])
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#94a3b8'))
        canvas.drawRightString(width - doc.rightMargin, 25, f"Page {doc.page}")
        canvas.restoreState()
    
    def _create_title_page(self, styles):
        """Create title page elements"""
        story = []
        
        # Title
        story.append(Spacer(1, 1.65*inch))
        story.append(HRFlowable(width='22%', thickness=4, color=colors.HexColor('#2563eb'),
                                hAlign='CENTER', spaceAfter=24))
        story.append(Paragraph(self.project_title, styles['CustomTitle']))
        story.append(Spacer(1, 0.5*inch))
        
        # Subtitle
        story.append(Paragraph(
            "PROJECT DOCUMENTATION",
            styles['Heading2']
        ))
        story.append(Spacer(1, 0.3*inch))
        
        # Date
        export_date = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        story.append(Paragraph(
            f"<i>Exported on {export_date}</i>",
            styles['Normal']
        ))
        
        return story
    
    def _build_toc(self):
        """Build table of contents by traversing the tree"""
        nodes = self.db.get_all_nodes_for_project(self.project_id)
        
        # Build tree structure
        node_dict = {n['id']: n for n in nodes}
        root_nodes = [n for n in nodes if n['parent_id'] is None]
        
        toc_items = []
        
        def traverse(node, level=0):
            toc_items.append({
                'id': node['id'],
                'name': node['name'],
                'type': node['node_type'],
                'level': level
            })
            
            # Get children
            children = [n for n in nodes if n['parent_id'] == node['id']]
            for child in sorted(children, key=lambda x: x['name']):
                traverse(child, level + 1)
        
        # Traverse from root nodes
        for root in sorted(root_nodes, key=lambda x: x['name']):
            traverse(root)
        
        return toc_items
    
    def _create_toc(self, toc_items, styles):
        """Create table of contents section"""
        story = []
        
        story.append(Paragraph("Table of Contents", styles['CustomHeading1']))
        story.append(Spacer(1, 0.2*inch))
        
        for item in toc_items:
            indent = item['level'] * 20
            icon = "SECTION" if item['type'] == 'folder' else "PAGE" if item['type'] == 'subpage' else "DIAGRAM"
            
            toc_style = ParagraphStyle(
                name=f'TOC{item["level"]}',
                parent=styles['Normal'],
                leftIndent=indent,
                fontSize=10
            )
            
            story.append(Paragraph(
                f"<font color='#64748b' size='7'>{icon}</font> &nbsp; {self._clean_text_for_pdf(item['name'])}",
                toc_style
            ))
            story.append(Spacer(1, 3))
        
        return story
    
    def _create_content(self, toc_items, styles):
        """Create content sections for all nodes"""
        story = []
        
        for item in toc_items:
            if item['type'] == 'folder':
                # Folder heading
                heading_style = self._get_heading_for_level(item['level'], styles)
                story.append(Paragraph(self._clean_text_for_pdf(item['name']), heading_style))
                story.append(Spacer(1, 0.1*inch))
                
            elif item['type'] == 'subpage':
                # Subpage content
                story.extend(self._create_subpage_content(item, styles))
                story.append(PageBreak())
                
            elif item['type'] == 'flowchart':
                # Flowchart as image
                story.extend(self._create_flowchart_content(item, styles))
                story.append(PageBreak())
        
        return story
    
    def _get_heading_for_level(self, level, styles):
        """Get appropriate heading style for tree level"""
        if level == 0:
            return styles['CustomHeading1']
        elif level == 1:
            return styles['CustomHeading2']
        else:
            return styles['CustomHeading3']
    
    def _create_subpage_content(self, item, styles):
        """Create content for a subpage with embedded images"""
        story = []
        
        # Heading
        heading_style = self._get_heading_for_level(item['level'], styles)
        story.append(Paragraph(self._clean_text_for_pdf(item['name']), heading_style))
        story.append(HRFlowable(width='100%', thickness=0.6, color=colors.HexColor('#cbd5e1'), spaceAfter=10))
        story.append(Spacer(1, 0.15*inch))
        
        # Load content
        content_data = self.db.load_subpage(item['id'])
        
        media_list = self.db.get_media_for_node(item['id'])

        if content_data:
            if isinstance(content_data, dict):
                content = content_data.get('content', '')
                tags = content_data.get('tags', {}) or {}
            else:
                content = content_data
                tags = {}
            
            if content:
                story.extend(self._render_rich_text(content, tags, styles))
            else:
                story.append(Paragraph("<i>No content</i>", styles['Normal']))
        else:
            story.append(Paragraph("<i>No content</i>", styles['Normal']))
        
        story.append(Spacer(1, 0.15*inch))
        
        if media_list:
            images = [m for m in media_list if m.get('media_type') == 'image']
            other_media = [m for m in media_list if m.get('media_type') != 'image']
            if images:
                story.append(Spacer(1, 0.12*inch))
                story.append(Paragraph("IMAGE ASSETS", styles['SectionLabel']))
                story.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#dbeafe'), spaceAfter=10))
            
            for number, media in enumerate(images, 1):
                media_type = media.get('media_type', '')
                file_path = media.get('file_path', '')
                original_filename = media.get('original_filename', 'unnamed')
                
                if media_type == 'image' and file_path and os.path.exists(file_path):
                    # Embed image in PDF
                    try:
                        img = Image(file_path)
                        
                        # Scale to fit page width (6.5 inches max)
                        max_width = 5 * inch  # Leave some margin
                        max_height = 4 * inch
                        
                        img_width, img_height = img.imageWidth, img.imageHeight
                        scale = min(max_width / img_width, max_height / img_height, 1.0)
                        
                        img.drawWidth = img_width * scale
                        img.drawHeight = img_height * scale
                        
                        caption = Paragraph(
                            f"Figure {number} — {self._clean_text_for_pdf(original_filename)}",
                            styles['Caption'])
                        story.append(KeepTogether([img, caption]))
                        
                    except Exception as e:
                        print(f"[Export] Failed to embed image {file_path}: {e}")
                        story.append(Paragraph(
                            f"• Image: {original_filename} (failed to load)",
                            styles['Normal']
                        ))
                        story.append(Spacer(1, 0.05*inch))
                
            if other_media:
                story.append(Paragraph("ATTACHMENTS", styles['SectionLabel']))
                rows = [['Type', 'File']]
                for media in other_media:
                    rows.append([media.get('media_type', 'file').upper(), media.get('original_filename', 'unnamed')])
                table = Table(rows, colWidths=[0.95*inch, 5.2*inch], repeatRows=1)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#334155')),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8.5),
                    ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#cbd5e1')),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]))
                story.append(table)
            
            story.append(Spacer(1, 0.1*inch))
        
        return story
    
    def _create_flowchart_content(self, item, styles):
        """Create content for a flowchart (export as PNG image)"""
        story = []
        
        # Heading
        heading_style = self._get_heading_for_level(item['level'], styles)
        story.append(Paragraph(self._clean_text_for_pdf(item['name']), heading_style))
        story.append(Spacer(1, 0.15*inch))
        
        # Export flowchart to temporary PNG
        temp_png = self._export_flowchart_to_png(item['id'])
        
        if temp_png and os.path.exists(temp_png):
            try:
                # Add image to PDF
                img = Image(temp_png)
                
                # Scale to fit page width (6.5 inches available with margins)
                max_width = 6.5 * inch
                max_height = 8 * inch
                
                img_width, img_height = img.imageWidth, img.imageHeight
                scale = min(max_width / img_width, max_height / img_height, 1.0)
                
                img.drawWidth = img_width * scale
                img.drawHeight = img_height * scale
                
                story.append(img)
                story.append(Spacer(1, 0.2*inch))
                
            except Exception as e:
                story.append(Paragraph(
                    f"<i>Error loading flowchart image: {str(e)}</i>",
                    styles['Normal']
                ))
        else:
            story.append(Paragraph("<i>Empty flowchart</i>", styles['Normal']))
        
        return story
    
    def _export_flowchart_to_png(self, node_id):
        """
        Export a flowchart to a temporary PNG file
        
        Returns:
            Path to temporary PNG file, or None if failed
        """
        try:
            # Load flowchart data
            data = self.db.load_subpage(node_id)
            
            if not data:
                return None
            
            # Parse flowchart state
            if isinstance(data, str):
                import json
                state = json.loads(data)
            else:
                state = data
            
            items = state.get('items', [])
            
            if not items:
                return None
            
            # Calculate bounding box
            min_x, min_y = float('inf'), float('inf')
            max_x, max_y = float('-inf'), float('-inf')
            
            for item in items:
                coords = item.get('coords', [])
                if coords:
                    for i in range(0, len(coords), 2):
                        if i + 1 < len(coords):
                            x, y = coords[i], coords[i + 1]
                            min_x = min(min_x, x)
                            min_y = min(min_y, y)
                            max_x = max(max_x, x)
                            max_y = max(max_y, y)
            
            # Add padding
            padding = 50
            min_x -= padding
            min_y -= padding
            max_x += padding
            max_y += padding
            
            width = int(max_x - min_x)
            height = int(max_y - min_y)
            
            if width <= 0 or height <= 0:
                return None
            
            # Create image
            img = PILImage.new('RGB', (width, height), color='#1e1e1e')
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(img)
            
            # Try to load font
            try:
                font = ImageFont.truetype("segoeui.ttf", 14)
                font_small = ImageFont.truetype("segoeui.ttf", 12)
            except:
                try:
                    font = ImageFont.truetype("arial.ttf", 14)
                    font_small = ImageFont.truetype("arial.ttf", 12)
                except:
                    font = ImageFont.load_default()
                    font_small = ImageFont.load_default()
            
            # Draw shapes
            for item in items:
                item_type = item.get('type')
                coords = item.get('coords', [])
                
                # Translate coordinates
                translated_coords = [
                    (coords[i] - min_x, coords[i+1] - min_y) 
                    for i in range(0, len(coords), 2)
                ]
                flat_coords = [c for pair in translated_coords for c in pair]
                
                fill = item.get('fill', '#444444')
                outline = item.get('outline', '#666666')
                width_val = int(item.get('width', 2))
                
                if item_type == 'rectangle' and len(flat_coords) >= 4:
                    draw.rectangle(flat_coords, fill=fill, outline=outline, width=width_val)
                    
                elif item_type == 'oval' and len(flat_coords) >= 4:
                    draw.ellipse(flat_coords, fill=fill, outline=outline, width=width_val)
                    
                elif item_type == 'polygon':
                    draw.polygon(flat_coords, fill=fill, outline=outline)
                    
                elif item_type == 'line' and len(flat_coords) >= 4:
                    draw.line(flat_coords, fill=fill, width=width_val)
                    
                    # Draw arrow if present
                    if item.get('arrow') == 'last' and len(flat_coords) >= 4:
                        x1, y1 = flat_coords[-2], flat_coords[-1]
                        x0, y0 = flat_coords[-4], flat_coords[-3]
                        
                        # Simple arrowhead
                        arrow_coords = [(x1, y1), (x1-10, y1-5), (x1-10, y1+5)]
                        draw.polygon(arrow_coords, fill=fill)
                
                # Draw text if present
                text_content = item.get('text', '')
                if text_content:
                    text_coords = item.get('text_coords', coords[:2] if coords else [0, 0])
                    if len(text_coords) >= 2:
                        tx = text_coords[0] - min_x
                        ty = text_coords[1] - min_y
                        
                        # Get text bounding box for centering
                        bbox = draw.textbbox((0, 0), text_content, font=font)
                        text_width = bbox[2] - bbox[0]
                        text_height = bbox[3] - bbox[1]
                        
                        draw.text(
                            (tx - text_width/2, ty - text_height/2),
                            text_content,
                            fill='#e0e0ff',
                            font=font
                        )
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            temp_path = temp_file.name
            temp_file.close()
            
            img.save(temp_path)
            self.temp_images.append(temp_path)
            
            return temp_path
            
        except Exception as e:
            print(f"[Export] Failed to export flowchart {node_id}: {e}")
            return None

    @staticmethod
    def _text_index_to_offset(content, position_index):
        """Convert a saved Tk index (line.column) into a string offset."""
        try:
            line_no, column = (int(value) for value in str(position_index).split('.', 1))
            lines = content.splitlines(keepends=True)
            if line_no < 1:
                return 0
            if line_no > len(lines):
                return len(content)
            return min(sum(len(line) for line in lines[:line_no - 1]) + column, len(content))
        except (TypeError, ValueError):
            return len(content)

    def _insert_media_markers(self, content, media_list):
        """Represent editor windows at their original locations in exported text."""
        insertions = []
        for media in media_list:
            if media.get('media_type') != 'image':
                continue
            name = media.get('original_filename') or 'unnamed'
            marker = f"{{image{{{name}}}}}"
            offset = self._text_index_to_offset(content, media.get('position_index'))
            insertions.append((offset, marker))

        # Descending offsets ensure earlier insertions do not shift later ones.
        for offset, marker in sorted(insertions, key=lambda value: value[0], reverse=True):
            before = '\n' if offset and content[offset - 1] != '\n' else ''
            after = '\n' if offset < len(content) and content[offset] != '\n' else ''
            content = content[:offset] + before + marker + after + content[offset:]
        return content

    def _render_document_text(self, content, styles):
        """Render prose, image references and triple-quote code as distinct blocks."""
        story = []
        pieces = __import__('re').split(r"('''.*?''')", content, flags=__import__('re').DOTALL)
        marker_pattern = __import__('re').compile(r'\{image\{([^}]+)\}\}')

        for piece in pieces:
            if not piece:
                continue
            if piece.startswith("'''") and piece.endswith("'''"):
                code = piece[3:-3].strip('\n')
                code_text = Preformatted(self._clean_text_for_pdf(code), styles['CodeBlock'])
                code_card = Table([[code_text]], colWidths=[6.15 * inch])
                code_card.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#0f172a')),
                    ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#334155')),
                    ('LEFTPADDING', (0, 0), (-1, -1), 11),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 11),
                    ('TOPPADDING', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
                ]))
                story.extend([Spacer(1, 5), code_card, Spacer(1, 8)])
                continue

            for paragraph in piece.split('\n'):
                if not paragraph.strip():
                    story.append(Spacer(1, 4))
                    continue
                match = marker_pattern.fullmatch(paragraph.strip())
                if match:
                    marker = self._clean_text_for_pdf(paragraph.strip())
                    story.append(Paragraph(marker, styles['ImageMarker']))
                else:
                    clean = self._clean_text_for_pdf(paragraph)
                    clean = marker_pattern.sub(
                        lambda m: "<font name='Courier' color='#2563eb'>" +
                                  self._clean_text_for_pdf(m.group(0)) + "</font>", clean)
                    story.append(Paragraph(clean, styles['CustomBody']))
        return story

    def _tag_offsets(self, content, tags):
        """Convert persisted Tk ranges into offset ranges for PDF rendering."""
        converted = {}
        for tag, ranges in (tags or {}).items():
            values = []
            for item in ranges:
                if not isinstance(item, (list, tuple)) or len(item) != 2:
                    continue
                start = self._text_index_to_offset(content, item[0])
                end = self._text_index_to_offset(content, item[1])
                if end > start:
                    values.append((start, end))
            if values:
                converted[tag] = values
        return converted

    @staticmethod
    def _active_tags(offset, converted):
        return {tag for tag, ranges in converted.items()
                if any(start <= offset < end for start, end in ranges)}

    def _resolve_pdf_font(self, requested, bold=False, italic=False):
        key = (requested.lower(), bold, italic)
        if key in self._pdf_font_cache:
            return self._pdf_font_cache[key]
        lowered = requested.lower()
        fallback = 'Courier' if ('courier' in lowered or 'consol' in lowered or 'mono' in lowered) \
            else ('Times-Roman' if ('times' in lowered or 'serif' in lowered) else 'Helvetica')
        normalized = ''.join(ch for ch in lowered if ch.isalnum())
        roots = [os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts'),
                 '/usr/share/fonts', '/usr/local/share/fonts']
        candidates = []
        for root in roots:
            if not os.path.isdir(root):
                continue
            for folder, _, files in os.walk(root):
                for filename in files:
                    if not filename.lower().endswith(('.ttf', '.otf')):
                        continue
                    stem = ''.join(ch for ch in os.path.splitext(filename)[0].lower() if ch.isalnum())
                    if stem == normalized or stem.startswith(normalized):
                        score = len(stem) - len(normalized)
                        wants = ('bold' if bold else '') + ('italic' if italic else '')
                        if wants and any(token in stem for token in (wants, 'bold', 'italic')):
                            score -= 2
                        candidates.append((score, os.path.join(folder, filename)))
        if candidates:
            try:
                path = min(candidates, key=lambda item: item[0])[1]
                registered = 'TarizzFont' + str(len(self._pdf_font_cache) + 1)
                pdfmetrics.registerFont(TTFont(registered, path))
                fallback = registered
            except Exception:
                pass
        self._pdf_font_cache[key] = fallback
        return fallback

    def _font_markup(self, tags):
        """Return ReportLab-safe opening/closing markup for character tags."""
        family, requested, size = 'Helvetica', 'Helvetica', 11
        bold = 'bold' in tags
        italic = 'italic' in tags
        for tag in tags:
            if tag.startswith('fmt_'):
                parts = tag.split('_')
                if len(parts) >= 5:
                    try:
                        size = max(6, min(96, int(parts[-3])))
                    except ValueError:
                        pass
                    bold = parts[-2] == 'bold'
                    italic = parts[-1] == 'italic'
                    requested = ' '.join(parts[1:-3])
            elif tag.startswith('size_'):
                try:
                    size = max(6, min(96, int(tag[5:])))
                except ValueError:
                    pass
            elif tag == 'inline_code':
                requested = 'Courier'

        family = self._resolve_pdf_font(requested, bold, italic)
        embedded_style = family.startswith('TarizzFont')

        attrs = [f"name='{family}'", f"size='{size}'"]
        for tag in tags:
            if tag.startswith('color_'):
                attrs.append(f"color='#{tag[6:]}'")
            elif tag.startswith('bgcolor_'):
                attrs.append(f"backColor='#{tag[8:]}'")
        opening = ['<font ' + ' '.join(attrs) + '>']
        closing = ['</font>']
        wrappers = []
        if bold and not embedded_style:
            wrappers.append(('b', '<b>', '</b>'))
        if italic and not embedded_style:
            wrappers.append(('i', '<i>', '</i>'))
        if 'underline' in tags:
            wrappers.append(('u', '<u>', '</u>'))
        if 'strike' in tags:
            wrappers.append(('strike', '<strike>', '</strike>'))
        if 'superscript' in tags:
            wrappers.append(('super', '<super>', '</super>'))
        if 'subscript' in tags:
            wrappers.append(('sub', '<sub>', '</sub>'))
        for tag in tags:
            if tag.startswith('link_'):
                href = self._xml_attribute(unquote(tag[5:]))
                wrappers.append(('link', f"<link href='{href}' color='#2563eb'>", '</link>'))
        for _, op, cl in wrappers:
            opening.append(op)
            closing.insert(0, cl)
        return ''.join(opening), ''.join(closing)

    @staticmethod
    def _font_size_for_tags(tags, default=11):
        size = default
        for tag in tags:
            if tag.startswith('fmt_'):
                try:
                    size = int(tag.split('_')[-3])
                except (ValueError, IndexError):
                    pass
            elif tag.startswith('size_'):
                try:
                    size = int(tag[5:])
                except ValueError:
                    pass
        return max(6, min(96, size))

    @staticmethod
    def _xml_attribute(value):
        return (str(value).replace('&', '&amp;').replace("'", '&apos;')
                .replace('<', '&lt;').replace('>', '&gt;'))

    def _render_rich_text(self, content, tags, styles):
        """Render editor ranges into styled PDF paragraphs without flattening."""
        converted = self._tag_offsets(content, tags)
        story = []
        position = 0
        style_cache = {}
        code_buffer = []

        def flush_code():
            if not code_buffer:
                return
            label = Paragraph("<font color='#7dd3fc'><b>CODE</b></font>", styles['SectionLabel'])
            code = Preformatted(self._clean_text_for_pdf('\n'.join(code_buffer)), styles['CodeBlock'])
            card = Table([[label], [code]], colWidths=[6.15 * inch])
            card.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#0b1220')),
                ('BOX', (0, 0), (-1, -1), 0.7, colors.HexColor('#334155')),
                ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.HexColor('#1e3a5f')),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.extend([Spacer(1, 6), card, Spacer(1, 9)])
            code_buffer.clear()

        for raw_line in content.splitlines(True):
            line = raw_line.rstrip('\r\n')
            if not line:
                in_code = any(start <= position < end for start, end in converted.get('code_block', []))
                if in_code:
                    code_buffer.append('')
                    position += len(raw_line)
                    continue
                flush_code()
                story.append(Spacer(1, 5))
                position += len(raw_line)
                continue

            line_tags = self._active_tags(position, converted)
            line_end_offset = position + len(line)
            is_code_line = any(start < line_end_offset and end > position
                               for start, end in converted.get('code_block', []))
            if is_code_line or "'''" in line:
                code_line = line.replace("'''", '')
                if code_line:
                    code_buffer.append(code_line)
                position += len(raw_line)
                continue
            flush_code()
            base_name = 'CustomBody'
            for candidate, pdf_style in (('style_title', 'CustomTitle'),
                                         ('style_heading1', 'CustomHeading1'),
                                         ('style_heading2', 'CustomHeading2'),
                                         ('style_heading3', 'CustomHeading3')):
                if candidate in line_tags:
                    base_name = pdf_style
                    break
            alignment = TA_LEFT
            if 'align_center' in line_tags:
                alignment = TA_CENTER
            elif 'align_right' in line_tags:
                alignment = TA_RIGHT
            elif 'align_justify' in line_tags:
                alignment = TA_JUSTIFY

            line_sizes = [self._font_size_for_tags(self._active_tags(position + i, converted))
                          for i in range(len(line))]
            max_line_size = max(line_sizes, default=styles[base_name].fontSize)
            dynamic_leading = max(styles[base_name].leading or styles[base_name].fontSize * 1.2,
                                  max_line_size * 1.25)
            cache_key = (base_name, alignment, 'quote' in line_tags, dynamic_leading)
            if cache_key not in style_cache:
                style_cache[cache_key] = ParagraphStyle(
                    'Rich_' + str(len(style_cache)), parent=styles[base_name],
                    alignment=alignment,
                    leading=dynamic_leading,
                    leftIndent=22 if 'quote' in line_tags else styles[base_name].leftIndent,
                    borderColor=colors.HexColor('#94a3b8') if 'quote' in line_tags else None,
                    borderWidth=1 if 'quote' in line_tags else 0,
                    borderPadding=6 if 'quote' in line_tags else 0,
                )

            boundaries = {0, len(line)}
            for ranges in converted.values():
                for start, end in ranges:
                    if start < position + len(line) and end > position:
                        boundaries.add(max(0, start - position))
                        boundaries.add(min(len(line), end - position))
            ordered = sorted(boundaries)
            markup = []
            for left, right in zip(ordered, ordered[1:]):
                if right <= left:
                    continue
                active = self._active_tags(position + left, converted)
                opening, closing = self._font_markup(active)
                markup.append(opening + self._clean_text_for_pdf(line[left:right]) + closing)
            story.append(Paragraph(''.join(markup) or '&nbsp;', style_cache[cache_key]))
            position += len(raw_line)

        flush_code()

        if content and not content.endswith(('\n', '\r')) and not story:
            story.append(Paragraph(self._clean_text_for_pdf(content), styles['CustomBody']))
        return story
    
    def _clean_text_for_pdf(self, text):
        """Clean text for PDF output (escape XML special chars)"""
        # Replace special characters that might break PDF
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        return text
    
    def _cleanup_temp_files(self):
        """Remove temporary image files"""
        for temp_file in self.temp_images:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
        self.temp_images.clear()


def export_project(project_id, project_title, db_module):
    """
    Convenience function to export a project to PDF
    
    Args:
        project_id: Database ID of the project
        project_title: Title of the project
        db_module: The database module with get_all_nodes_for_project and load_subpage functions
    
    Returns:
        True if successful, False otherwise
    """
    exporter = ProjectExporter(project_id, project_title, db_module)
    return exporter.export_to_pdf()
