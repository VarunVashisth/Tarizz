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
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas as pdf_canvas
from PIL import Image as PILImage
import tkinter as tk
from tkinter import filedialog, messagebox


class ProjectExporter:
    """Handles exporting a project to PDF"""
    
    def __init__(self, project_id, project_title, db_module):
        self.project_id = project_id
        self.project_title = project_title
        self.db = db_module
        self.temp_images = []  # Track temp files for cleanup
        
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
                pagesize=letter,
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
            doc.build(story)
            
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
    
    def _create_title_page(self, styles):
        """Create title page elements"""
        story = []
        
        # Title
        story.append(Spacer(1, 2*inch))
        story.append(Paragraph(self.project_title, styles['CustomTitle']))
        story.append(Spacer(1, 0.5*inch))
        
        # Subtitle
        story.append(Paragraph(
            "Complete Project Export",
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
            icon = "📁" if item['type'] == 'folder' else "📄" if item['type'] == 'subpage' else "📊"
            
            toc_style = ParagraphStyle(
                name=f'TOC{item["level"]}',
                parent=styles['Normal'],
                leftIndent=indent,
                fontSize=10
            )
            
            story.append(Paragraph(
                f"{icon} {item['name']}",
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
                story.append(Paragraph(f"📁 {item['name']}", heading_style))
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
        story.append(Paragraph(f"📄 {item['name']}", heading_style))
        story.append(Spacer(1, 0.15*inch))
        
        # Load content
        content_data = self.db.load_subpage(item['id'])
        
        if content_data:
            if isinstance(content_data, dict):
                content = content_data.get('content', '')
            else:
                content = content_data
            
            if content:
                # Split into paragraphs and add to story
                paragraphs = content.split('\n')
                for para in paragraphs:
                    if para.strip():
                        # Clean up the text for PDF
                        clean_para = self._clean_text_for_pdf(para)
                        story.append(Paragraph(clean_para, styles['CustomBody']))
                        story.append(Spacer(1, 0.05*inch))
            else:
                story.append(Paragraph("<i>No content</i>", styles['Normal']))
        else:
            story.append(Paragraph("<i>No content</i>", styles['Normal']))
        
        story.append(Spacer(1, 0.15*inch))
        
        # Get media for this subpage
        media_list = self.db.get_media_for_node(item['id'])
        
        if media_list:
            story.append(Paragraph("<b>Attached Media:</b>", styles['Normal']))
            story.append(Spacer(1, 0.1*inch))
            
            for media in media_list:
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
                        
                        story.append(img)
                        story.append(Spacer(1, 0.1*inch))
                        story.append(Paragraph(
                            f"<i>Image: {original_filename}</i>",
                            styles['Normal']
                        ))
                        story.append(Spacer(1, 0.15*inch))
                        
                    except Exception as e:
                        print(f"[Export] Failed to embed image {file_path}: {e}")
                        story.append(Paragraph(
                            f"• Image: {original_filename} (failed to load)",
                            styles['Normal']
                        ))
                        story.append(Spacer(1, 0.05*inch))
                
                elif media_type == 'video':
                    # List video file name
                    story.append(Paragraph(
                        f"• 🎥 Video: {original_filename}",
                        styles['Normal']
                    ))
                    story.append(Spacer(1, 0.05*inch))
                
                elif media_type == 'pdf':
                    # List PDF file name
                    story.append(Paragraph(
                        f"• 📄 PDF Document: {original_filename}",
                        styles['Normal']
                    ))
                    story.append(Spacer(1, 0.05*inch))
                
                elif media_type == 'doc':
                    # List document file name
                    story.append(Paragraph(
                        f"• 📝 Document: {original_filename}",
                        styles['Normal']
                    ))
                    story.append(Spacer(1, 0.05*inch))
            
            story.append(Spacer(1, 0.1*inch))
        
        return story
    
    def _create_flowchart_content(self, item, styles):
        """Create content for a flowchart (export as PNG image)"""
        story = []
        
        # Heading
        heading_style = self._get_heading_for_level(item['level'], styles)
        story.append(Paragraph(f"📊 {item['name']}", heading_style))
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