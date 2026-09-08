"""Modern single-window Tarizz workspace built with PyQt6."""
import json
import os
import shutil
import uuid
from datetime import date

from PyQt6.QtCore import QDate, QEvent, QLineF, QPointF, QRectF, QRegularExpression, Qt, QTimer, QUrl, pyqtSignal as Signal
from PyQt6.QtGui import QAction, QBrush, QColor, QDesktopServices, QFont, QImage, QKeySequence, QPainter, QPen, QPolygonF, QSyntaxHighlighter, QTextBlockFormat, QTextCharFormat, QTextCursor, QTextDocument, QTextImageFormat, QTextLength, QTextListFormat, QTextTableFormat
from PyQt6.QtWidgets import (
    QApplication, QCalendarWidget, QCheckBox, QColorDialog, QComboBox, QDateEdit,
    QFileDialog, QFrame, QGraphicsEllipseItem, QGraphicsItem, QGraphicsLineItem,
    QGraphicsPolygonItem, QGraphicsRectItem, QGraphicsScene, QGraphicsTextItem,
    QGraphicsView, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QSplitter, QStackedWidget, QTabWidget, QTextBrowser,
    QTextEdit, QToolBar, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from backend.database import get_db


STYLE = """
* { font-family: "Inter", "Segoe UI", sans-serif; font-size: 13px; color: #dcddde; }
QMainWindow, QWidget#root, QStackedWidget { background: #181818; }
QToolTip { background:#2b2b2b; color:#eee; border:1px solid #484848; padding:5px; }
QFrame#rail { background:#151515; border-right:1px solid #2b2b2b; }
QFrame#sidebar { background:#202020; border-right:1px solid #303030; }
QFrame#editorHeader, QFrame#status { background:#1b1b1b; }
QLabel#brand { font-size:15px; font-weight:700; color:#eeeeee; }
QLabel#eyebrow { font-size:10px; font-weight:600; color:#77777d; letter-spacing:1px; }
QLabel#pageTitle { font-size:24px; font-weight:700; color:#f0f0f0; }
QLabel#muted { color:#88888e; }
QPushButton { background:transparent; border:0; border-radius:5px; padding:7px 10px; text-align:left; }
QPushButton:hover { background:#2d2d2d; }
QPushButton:pressed, QPushButton:checked { background:#37334a; color:#c9c2ff; }
QPushButton#railButton { font-size:19px; padding:9px; text-align:center; }
QPushButton#primary { background:#6c5dd3; color:white; font-weight:600; padding:8px 13px; }
QPushButton#primary:hover { background:#7d6fe0; }
QPushButton#danger:hover { background:#472929; color:#ffb4b4; }
QLineEdit, QComboBox, QDateEdit { background:#262626; border:1px solid #393939; border-radius:5px; padding:7px 9px; selection-background-color:#5c50ad; }
QLineEdit:focus, QComboBox:focus, QDateEdit:focus { border-color:#7163cc; }
QListWidget, QTreeWidget { background:#202020; border:0; outline:0; padding:3px; }
QListWidget::item, QTreeWidget::item { border-radius:4px; padding:6px; }
QListWidget::item:hover, QTreeWidget::item:hover { background:#292929; }
QListWidget::item:selected, QTreeWidget::item:selected { background:#37334a; color:#f0edff; }
QTabWidget::pane { border:0; background:#181818; }
QTabBar::tab { background:#202020; color:#99999f; border-right:1px solid #303030; padding:9px 16px; }
QTabBar::tab:selected { background:#181818; color:#eeeeee; border-top:2px solid #7c6fdd; }
QTextEdit, QTextBrowser { background:#181818; border:0; padding:24px 54px; selection-background-color:#4c456d; font-size:15px; }
QToolBar { background:#202020; border:0; border-bottom:1px solid #303030; spacing:2px; padding:4px 10px; }
QToolButton { background:transparent; border:0; border-radius:4px; padding:6px 8px; }
QToolButton:hover { background:#303030; }
QToolButton:checked { background:#40395c; color:#d8d2ff; }
QCalendarWidget QWidget { alternate-background-color:#202020; }
QCalendarWidget QAbstractItemView { background:#202020; selection-background-color:#6c5dd3; outline:0; }
QScrollBar:vertical { background:#181818; width:10px; }
QScrollBar::handle:vertical { background:#3a3a3a; min-height:30px; border-radius:5px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QSplitter::handle { background:#303030; width:1px; }
"""


def button(text, callback=None, name=None, checkable=False):
    item = QPushButton(text)
    if name:
        item.setObjectName(name)
    item.setCheckable(checkable)
    if callback:
        item.clicked.connect(callback)
    item.setCursor(Qt.CursorShape.PointingHandCursor)
    return item


class MediaTextEdit(QTextEdit):
    """Rich editor with direct horizontal drag resizing for embedded images."""
    imageResized=Signal()
    def __init__(self,parent=None):super().__init__(parent);self._image_drag=None;self.setMouseTracking(True)
    def image_selection_at(self,point):
        base=self.cursorForPosition(point).position()
        for start in (base,base-1):
            if start<0 or start>=self.document().characterCount()-1:continue
            cursor=QTextCursor(self.document());cursor.setPosition(start);cursor.movePosition(QTextCursor.MoveOperation.NextCharacter,QTextCursor.MoveMode.KeepAnchor);fmt=cursor.charFormat()
            # QTextCursor can inherit the format from the character beside an
            # image.  The object replacement character is the reliable hit-test.
            if cursor.selectedText()=='\ufffc' and fmt.isImageFormat():return start,fmt.toImageFormat()
        return None,None
    def apply_image_width(self,start,width,ratio=None):
        cursor=QTextCursor(self.document());cursor.setPosition(start);cursor.movePosition(QTextCursor.MoveOperation.NextCharacter,QTextCursor.MoveMode.KeepAnchor);fmt=cursor.charFormat().toImageFormat();fmt.setWidth(width)
        if ratio:fmt.setHeight(width/ratio)
        cursor.setCharFormat(fmt)
    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:
            start,fmt=self.image_selection_at(event.position().toPoint())
            if fmt is not None:
                width=max(1.0,fmt.width());height=max(1.0,fmt.height());self._image_drag=(start,event.position().x(),width,width/height);self.viewport().setCursor(Qt.CursorShape.SizeHorCursor);event.accept();return
        super().mousePressEvent(event)
    def mouseMoveEvent(self,event):
        if self._image_drag:
            start,start_x,start_width,ratio=self._image_drag;width=max(100,min(1400,start_width+(event.position().x()-start_x)));self.apply_image_width(start,width,ratio);self.imageResized.emit();event.accept();return
        start,_=self.image_selection_at(event.position().toPoint());self.viewport().setCursor(Qt.CursorShape.SizeHorCursor if start is not None else Qt.CursorShape.IBeamCursor);super().mouseMoveEvent(event)
    def mouseReleaseEvent(self,event):
        if self._image_drag:self._image_drag=None;self.viewport().setCursor(Qt.CursorShape.IBeamCursor);self.imageResized.emit();event.accept();return
        super().mouseReleaseEvent(event)


class CodeBlockHighlighter(QSyntaxHighlighter):
    """Small language-neutral highlighter, scoped to editor code tables."""
    def __init__(self,document):
        super().__init__(document)
        self.rules=[]
        def rule(pattern,color,bold=False,italic=False):
            fmt=QTextCharFormat();fmt.setForeground(QColor(color));fmt.setFontWeight(QFont.Weight.Bold if bold else QFont.Weight.Normal);fmt.setFontItalic(italic);self.rules.append((QRegularExpression(pattern),fmt))
        rule(r'\b(class|def|return|if|else|elif|for|while|in|import|from|as|try|except|finally|with|lambda|True|False|None|const|let|var|function|async|await|new|public|private)\b','#c4a7e7',True)
        rule(r'("[^"\n]*"|\'[^\'\n]*\')','#a6da95')
        rule(r'\b\d+(?:\.\d+)?\b','#f5a97f')
        rule(r'\b[A-Za-z_]\w*(?=\s*\()','#8aadf4')
        rule(r'(#|//).*$', '#7f849c',False,True)
    def highlightBlock(self,text):
        if QTextCursor(self.currentBlock()).currentTable() is None:return
        base=QTextCharFormat();base.setForeground(QColor('#e6e9ef'));base.setFontFamilies(['JetBrains Mono','Consolas','monospace']);self.setFormat(0,len(text),base)
        for expression,fmt in self.rules:
            match=expression.globalMatch(text)
            while match.hasNext():
                result=match.next();self.setFormat(result.capturedStart(),result.capturedLength(),fmt)


class RichEditor(QWidget):
    changed = Signal()

    def __init__(self, db, node, parent=None):
        super().__init__(parent)
        self.db, self.node = db, node
        self.setObjectName('root')
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
        header = QFrame(objectName='editorHeader'); row = QHBoxLayout(header); row.setContentsMargins(34, 18, 24, 12)
        title = QLabel(node['name'], objectName='pageTitle'); row.addWidget(title); row.addStretch()
        row.addWidget(QLabel('Local  ·  Encrypted', objectName='muted')); layout.addWidget(header)
        self.toolbar = QToolBar(); self.toolbar.setMovable(False); layout.addWidget(self.toolbar)
        self.edit = MediaTextEdit(); self.edit.setAcceptRichText(True); self.edit.setPlaceholderText('Start writing…')
        self.edit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu);self.edit.customContextMenuRequested.connect(self._context_menu);self.edit.viewport().installEventFilter(self)
        self.edit.document().setDefaultFont(QFont('Inter', 12));self.code_highlighter=CodeBlockHighlighter(self.edit.document()); layout.addWidget(self.edit, 1)
        status = QFrame(objectName='status'); status_row = QHBoxLayout(status); status_row.setContentsMargins(18, 5, 18, 5)
        self.save_label = QLabel('Saved', objectName='muted'); self.count_label = QLabel(objectName='muted')
        status_row.addWidget(self.save_label);status_row.addWidget(QLabel('  ·  Ctrl+Enter exits code  ·  Drag an image sideways to resize',objectName='muted'));status_row.addStretch(); status_row.addWidget(self.count_label); layout.addWidget(status)
        self.preview = None
        self.media = {}
        self.timer = QTimer(self); self.timer.setSingleShot(True); self.timer.timeout.connect(self.save)
        self._build_toolbar(); self._load();self.edit.imageResized.connect(self._on_change)
        self.edit.textChanged.connect(self._on_change)

    def _action(self, text, slot, shortcut=None, checkable=False, tip=None):
        action = QAction(text, self); action.setCheckable(checkable); action.triggered.connect(slot)
        if shortcut: action.setShortcut(QKeySequence(shortcut))
        if tip: action.setToolTip(tip)
        self.toolbar.addAction(action); return action

    def _build_toolbar(self):
        self._action('B', lambda v: self.edit.setFontWeight(QFont.Weight.Bold if v else QFont.Weight.Normal), 'Ctrl+B', True, 'Bold')
        self._action('I', self.edit.setFontItalic, 'Ctrl+I', True, 'Italic')
        self._action('U', self.edit.setFontUnderline, 'Ctrl+U', True, 'Underline')
        self.toolbar.addSeparator()
        styles = QComboBox(); styles.addItems(['Paragraph', 'Title', 'Heading 1', 'Heading 2', 'Heading 3'])
        styles.currentTextChanged.connect(self._set_style); self.toolbar.addWidget(styles)
        self._action('• List', self._bullet_list, tip='Bulleted list')
        self._action('1. List', self._number_list, tip='Numbered list')
        self._action('Link', self._link, 'Ctrl+K')
        self._action('Color', self._color)
        self._action('{ } Code block', self._code_block, 'Ctrl+Alt+C')
        self.toolbar.addSeparator()
        self._action('Image', lambda:self._insert_media('image'))
        self._action('Video', lambda:self._insert_media('video'))
        self._action('Document', lambda:self._insert_media('doc'))
        self.toolbar.addSeparator()
        self._action('Markdown preview', self.toggle_preview, 'Ctrl+Shift+M', True)
        self._action('Export page', self._export_page, 'Ctrl+Shift+E')
        self._action('Paste plain', self.paste_plain, 'Ctrl+Shift+V')

    def _set_style(self, name):
        sizes = {'Paragraph':12, 'Title':26, 'Heading 1':22, 'Heading 2':18, 'Heading 3':15}
        fmt = QTextCharFormat(); fmt.setFontPointSize(sizes[name]); fmt.setFontWeight(QFont.Weight.Bold if name not in ('Paragraph','Code') else QFont.Weight.Normal)
        cursor=self.edit.textCursor();cursor.mergeCharFormat(fmt)
        block_format=cursor.blockFormat();block_format.setHeadingLevel({'Title':1,'Heading 1':1,'Heading 2':2,'Heading 3':3}.get(name,0));block_format.setTopMargin(10 if name!='Paragraph' else 0);block_format.setBottomMargin(5 if name!='Paragraph' else 0);cursor.mergeBlockFormat(block_format);self.edit.setTextCursor(cursor)

    def _code_block(self):
        cursor=self.edit.textCursor()
        if cursor.currentTable() is not None:
            return
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        code=cursor.selectedText().replace('\u2029','\n') or 'Write code here…';cursor.beginEditBlock();cursor.removeSelectedText()
        table_format=QTextTableFormat();table_format.setWidth(QTextLength(QTextLength.Type.PercentageLength,100));table_format.setBorder(.8);table_format.setBorderBrush(QBrush(QColor('#343b4f')));table_format.setBorderStyle(QTextTableFormat.BorderStyle.BorderStyle_Solid);table_format.setBorderCollapse(True);table_format.setCellPadding(14);table_format.setCellSpacing(0);table_format.setBackground(QColor('#111827'));table_format.setTopMargin(8);table_format.setBottomMargin(8)
        table=cursor.insertTable(1,1,table_format);table_cell=table.cellAt(0,0);cell_format=table_cell.format();cell_format.setBackground(QColor('#111827'));table_cell.setFormat(cell_format);cell=table_cell.firstCursorPosition();char=QTextCharFormat();char.setFontFamilies(['JetBrains Mono','Consolas','monospace']);char.setFontPointSize(10.5);char.setForeground(QColor('#e6e9ef'));cell.setCharFormat(char);cell.insertText(code,char);cursor.endEditBlock();self.edit.setTextCursor(cell)

    def _bullet_list(self):
        self.edit.textCursor().createList(QTextListFormat.Style.ListDisc)

    def _number_list(self):
        self.edit.textCursor().createList(QTextListFormat.Style.ListDecimal)

    def _link(self):
        url, ok = QInputDialog.getText(self, 'Insert link', 'URL')
        if ok and url:
            fmt = QTextCharFormat(); fmt.setAnchor(True); fmt.setAnchorHref(url); fmt.setForeground(QColor('#9b8cff')); fmt.setFontUnderline(True)
            self.edit.textCursor().mergeCharFormat(fmt)

    def _color(self):
        color = QColorDialog.getColor(parent=self)
        if color.isValid(): self.edit.setTextColor(color)

    def paste_plain(self):
        clipboard = QApplication.clipboard(); self.edit.insertPlainText(clipboard.text())

    def toggle_preview(self, checked):
        if checked:
            self.preview = QTextBrowser(); self.preview.setOpenExternalLinks(True); self.preview.setMarkdown(self.edit.toPlainText())
            self.layout().replaceWidget(self.edit, self.preview); self.edit.hide(); self.preview.show()
        elif self.preview:
            self.layout().replaceWidget(self.preview, self.edit); self.preview.deleteLater(); self.preview = None; self.edit.show()

    def _insert_media(self,kind):
        filters={'image':'Images (*.png *.jpg *.jpeg *.gif *.webp)','video':'Videos (*.mp4 *.mov *.avi *.mkv *.webm)','doc':'Documents (*.pdf *.doc *.docx *.txt *.md *.odt)'}
        path,_=QFileDialog.getOpenFileName(self,f'Insert {kind}', '', filters[kind]+';;All files (*)')
        if not path:return
        try:
            stored=self.db.import_media_file(path);media_id=self.db.save_media(self.node['id'],kind,stored,os.path.basename(path),str(self.edit.textCursor().position()));record={'id':media_id,'media_type':kind,'file_path':stored,'original_filename':os.path.basename(path)};self.media[media_id]=record;self._insert_media_record(record);self._on_change()
        except Exception as exc:QMessageBox.critical(self,'Insert failed',str(exc))

    def _insert_media_record(self,record):
        cursor=self.edit.textCursor();cursor=self._cursor_after_table(cursor);cursor.insertBlock();kind=record['media_type'];path=record['file_path'];media_id=record['id'];name=record.get('original_filename') or os.path.basename(path)
        if kind=='image':
            image=QImage(path)
            if image.isNull():return
            fmt=QTextImageFormat();fmt.setName(QUrl.fromLocalFile(path).toString());width=min(620,max(160,image.width()));fmt.setWidth(width);fmt.setHeight(width*image.height()/max(1,image.width()));cursor.insertImage(fmt);cursor.insertBlock()
        else:
            icon='▶' if kind=='video' else '▤';cursor.insertHtml(f'<p><a href="tarizz-media://{media_id}" style="text-decoration:none"><b>{icon}&nbsp;&nbsp;{self._escape(name)}</b></a><br><span style="color:#808085">Double-click to open · Right-click for actions</span></p>');cursor.insertBlock()
        self.edit.setTextCursor(cursor)

    @staticmethod
    def _escape(value):return value.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

    def _media_at(self,pos):
        image_start,image_format=self.edit.image_selection_at(pos)
        if image_format is not None:
            cursor=QTextCursor(self.edit.document());cursor.setPosition(image_start)
            path=QUrl(image_format.name()).toLocalFile() or image_format.name();record=next((m for m in self.media.values() if os.path.abspath(m['file_path'])==os.path.abspath(path)),None);return cursor,record,True
        cursor=self.edit.cursorForPosition(pos);fmt=cursor.charFormat()
        href=fmt.anchorHref()
        if href.startswith('tarizz-media://'):
            try:return cursor,self.media.get(int(href.rsplit('/',1)[-1])),False
            except ValueError:pass
        return cursor,None,False

    def _context_menu(self,pos):
        cursor,record,is_image=self._media_at(pos);menu=self.edit.createStandardContextMenu()
        if record:
            menu.addSeparator();menu.addAction('Open in default app',lambda:self._open_media(record));menu.addAction('Save a copy…',lambda:self._download_media(record))
            if is_image:menu.addAction('Resize by dragging horizontally',lambda:None).setEnabled(False)
            menu.addAction('Remove embedded media',lambda:self._remove_media(cursor,record,is_image))
        menu.exec(self.edit.viewport().mapToGlobal(pos))

    def eventFilter(self,obj,event):
        if obj is self.edit.viewport() and event.type()==QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter) and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            cursor=self.edit.textCursor()
            if cursor.currentTable() is not None:
                self.edit.setTextCursor(self._cursor_after_table(cursor));return True
        if obj is self.edit.viewport() and event.type()==QEvent.Type.MouseButtonDblClick:
            _,record,_=self._media_at(event.position().toPoint())
            if record:self._open_media(record);return True
        return super().eventFilter(obj,event)

    @staticmethod
    def _cursor_after_table(cursor):
        table=cursor.currentTable()
        if table is None:return cursor
        outside=table.lastCursorPosition()
        if not outside.movePosition(QTextCursor.MoveOperation.NextBlock):
            outside.movePosition(QTextCursor.MoveOperation.End);outside.insertBlock()
        return outside

    def _open_media(self,record):QDesktopServices.openUrl(QUrl.fromLocalFile(record['file_path']))
    def _download_media(self,record):
        path,_=QFileDialog.getSaveFileName(self,'Save a copy',record.get('original_filename') or os.path.basename(record['file_path']))
        if path:
            try:shutil.copy2(record['file_path'],path)
            except OSError as exc:QMessageBox.critical(self,'Save failed',str(exc))
    def _remove_media(self,cursor,record,is_image):
        if is_image:
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter,QTextCursor.MoveMode.KeepAnchor);cursor.removeSelectedText()
        else:
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor);cursor.removeSelectedText();cursor.deleteChar()
        self.db.delete_media(record['id']);self.media.pop(record['id'],None);self._on_change()

    def _export_page(self):
        path,selected=QFileDialog.getSaveFileName(self,'Export current page',self.node['name'], 'PDF (*.pdf);;Markdown (*.md);;HTML (*.html);;Plain text (*.txt)')
        if not path:return
        try:
            if 'PDF' in selected:
                if not path.lower().endswith('.pdf'):path+='.pdf'
                self.save()
                import backend.database as database
                from project_export import ProjectExporter
                ProjectExporter(self.node.get('project_id'),self.node['name'],database).export_page_to_pdf(self.node['id'],self.node['name'],path)
            elif 'Markdown' in selected:
                if not path.lower().endswith('.md'):path+='.md'
                with open(path,'w',encoding='utf-8') as f:f.write(self._export_text_with_code_fences())
            elif 'HTML' in selected:
                if not path.lower().endswith('.html'):path+='.html'
                with open(path,'w',encoding='utf-8') as f:f.write(self.edit.toHtml())
            else:
                if not path.lower().endswith('.txt'):path+='.txt'
                with open(path,'w',encoding='utf-8') as f:f.write(self._export_text_with_code_fences())
            self.save_label.setText('Page exported')
        except Exception as exc:QMessageBox.critical(self,'Export failed',str(exc))

    def _load(self):
        dump = self.db.load_subpage(self.node['id']) or {}
        if isinstance(dump, str): self.edit.setPlainText(dump)
        elif dump.get('html'): self.edit.setHtml(dump['html'])
        else: self.edit.setPlainText(dump.get('content', ''))
        self.media={m['id']:m for m in self.db.get_media_for_node(self.node['id'])}
        html=self.edit.toHtml()
        for record in self.media.values():
            marker=f"tarizz-media://{record['id']}";path_url=QUrl.fromLocalFile(record['file_path']).toString()
            if marker not in html and path_url not in html:self._insert_media_record(record)
        self._update_count()

    def _on_change(self):
        self.save_label.setText('Unsaved changes'); self.timer.start(700); self._update_count(); self.changed.emit()

    def _update_count(self):
        value = self.edit.toPlainText(); self.count_label.setText(f'{len(value.split())} words  ·  {len(value)} characters')

    def save(self):
        seen=set();ordered_media=[]
        for pos in range(self.edit.document().characterCount()-1):
            cursor=QTextCursor(self.edit.document());cursor.setPosition(pos);cursor.movePosition(QTextCursor.MoveOperation.NextCharacter,QTextCursor.MoveMode.KeepAnchor);fmt=cursor.charFormat();media_id=None
            if fmt.isImageFormat():
                path=QUrl(fmt.toImageFormat().name()).toLocalFile() or fmt.toImageFormat().name();record=next((m for m in self.media.values() if os.path.abspath(m['file_path'])==os.path.abspath(path)),None);media_id=record['id'] if record else None
            elif fmt.anchorHref().startswith('tarizz-media://'):
                try:media_id=int(fmt.anchorHref().rsplit('/',1)[-1])
                except ValueError:pass
            if media_id and media_id not in seen:ordered_media.append((media_id,fmt.isImageFormat()));seen.add(media_id)
        export_content=self._export_text_with_code_fences();image_offsets=[i for i,ch in enumerate(export_content) if ch=='\ufffc'];image_index=0;search_from=0
        for media_id,is_image in ordered_media:
            if is_image and image_index<len(image_offsets):position=image_offsets[image_index];image_index+=1
            else:
                record=self.media.get(media_id,{})
                position=export_content.find(record.get('original_filename',''),search_from)
                if position<0:position=search_from
            self.db.update_media(media_id,str(position));search_from=max(search_from,position+1)
        self.db.save_subpage(self.node['id'], {'content':export_content, 'html':self.edit.toHtml(), 'tags':{}})
        self.save_label.setText('Saved')

    def _export_text_with_code_fences(self):
        """Serialize visible blocks while retaining semantic code containers."""
        lines=[];active_table=None;block=self.edit.document().begin()
        while block.isValid():
            cursor=QTextCursor(block);table=cursor.currentTable()
            if table is not active_table:
                if active_table is not None:lines.append('```')
                if table is not None:lines.append('```')
                active_table=table
            text=block.text() if table is not None else self._markdown_for_block(block)
            block_format=block.blockFormat();heading=block_format.headingLevel()
            if table is None and heading:text='#'*heading+' '+text
            text_list=block.textList()
            if table is None and text_list is not None:
                ordered=text_list.format().style() in (QTextListFormat.Style.ListDecimal,QTextListFormat.Style.ListLowerAlpha,QTextListFormat.Style.ListUpperAlpha,QTextListFormat.Style.ListLowerRoman,QTextListFormat.Style.ListUpperRoman)
                text=('1. ' if ordered else '- ')+text
            lines.append(text);block=block.next()
        if active_table is not None:lines.append('```')
        return '\n'.join(lines).strip('\n')

    @staticmethod
    def _markdown_for_block(block):
        """Keep the editor's useful inline formatting in portable exports."""
        parts=[];iterator=block.begin()
        while not iterator.atEnd():
            fragment=iterator.fragment();iterator+=1
            if not fragment.isValid():continue
            text=fragment.text();fmt=fragment.charFormat()
            if not text:continue
            href=fmt.anchorHref()
            if href and not href.startswith('tarizz-media://'):text=f'[{text}]({href})'
            if int(fmt.fontWeight())>=int(QFont.Weight.Bold):text=f'**{text}**'
            if fmt.fontItalic():text=f'*{text}*'
            if fmt.fontUnderline():text=f'<u>{text}</u>'
            parts.append(text)
        return ''.join(parts)


class DiagramView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene);self.setRenderHint(QPainter.RenderHint.Antialiasing);self.setDragMode(QGraphicsView.DragMode.RubberBandDrag);self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
    def drawBackground(self,painter,rect):
        painter.fillRect(rect,QColor('#fbfbfb'))
        pen=QPen(QColor('#e8e8eb'));pen.setWidthF(0.0);painter.setPen(pen);step=24
        left=int(rect.left())-(int(rect.left())%step);top=int(rect.top())-(int(rect.top())%step)
        lines=[]
        for x in range(left,int(rect.right()),step):lines.append(QLineF(x,rect.top(),x,rect.bottom()))
        for y in range(top,int(rect.bottom()),step):lines.append(QLineF(rect.left(),y,rect.right(),y))
        painter.drawLines(lines)
    def wheelEvent(self,event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor=1.15 if event.angleDelta().y()>0 else 1/1.15;self.scale(factor,factor);event.accept()
        else:super().wheelEvent(event)


class ConnectorItem(QGraphicsLineItem):
    def __init__(self,source=None,target=None,arrow=False,line=None):
        super().__init__(line or QLineF());self.source=source;self.target=target;self.arrow=arrow;self.setPen(QPen(QColor('#18181a'),2));self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable);self.setZValue(-1);self.head=QGraphicsPolygonItem(self);self.head.setBrush(QColor('#18181a'));self.head.setPen(QPen(QColor('#18181a')));self.head.setVisible(arrow);self.update_position()
    def update_position(self):
        if self.source is not None and self.target is not None:
            source_center=self.source.sceneBoundingRect().center();target_center=self.target.sceneBoundingRect().center();start=self.boundary_point(self.source,target_center);end=self.boundary_point(self.target,source_center);self.setLine(QLineF(start,end))
        line=self.line();b=line.p2();a=line.p1()
        if self.arrow and line.length()>0:
            import math
            angle=math.atan2(-(b.y()-a.y()),b.x()-a.x());size=12;p1=b-QPointF(math.sin(angle+math.pi/3)*size,math.cos(angle+math.pi/3)*size);p2=b-QPointF(math.sin(angle+math.pi-math.pi/3)*size,math.cos(angle+math.pi-math.pi/3)*size);self.head.setPolygon(QPolygonF([b,p1,p2]));self.head.setVisible(True)
    @staticmethod
    def boundary_point(item,toward):
        import math
        bounds=item.sceneBoundingRect();center=bounds.center();dx=toward.x()-center.x();dy=toward.y()-center.y()
        if not dx and not dy:return center
        rx=max(1.0,bounds.width()/2);ry=max(1.0,bounds.height()/2)
        if isinstance(item,QGraphicsEllipseItem):scale=1.0/math.sqrt((dx/rx)**2+(dy/ry)**2)
        else:scale=min(rx/abs(dx) if dx else float('inf'),ry/abs(dy) if dy else float('inf'))
        return center+QPointF(dx*scale,dy*scale)
    def detach(self):self.source=None;self.target=None


class FlowchartPage(QWidget):
    """Integrated diagram editor with the original editor's core tool set."""
    def __init__(self, db, node):
        super().__init__();self.db,self.node=db,node;self.loading=True
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0)
        tools=QToolBar();tools.setMovable(False);layout.addWidget(tools)
        self.scene=QGraphicsScene(-1500,-1000,3000,2000,self);self.view=DiagramView(self.scene);layout.addWidget(self.view,1);self.refreshing=False
        actions=[('▣ Rectangle',self.rect),('◯ Oval',self.ellipse),('◇ Diamond',self.diamond),('T Text',self.text),('— Line',lambda:self.connector(False)),('→ Arrow',lambda:self.connector(True)),('Detach',self.detach),('⌫ Delete',self.delete),('＋ Zoom',lambda:self.view.scale(1.2,1.2)),('− Zoom',lambda:self.view.scale(.8,.8)),('Fit',self.fit),('Export PNG',self.export_png)]
        for label,fn in actions:a=tools.addAction(label);a.triggered.connect(fn)
        delete_action=QAction(self);delete_action.setShortcut(QKeySequence.StandardKey.Delete);delete_action.triggered.connect(self.delete);self.addAction(delete_action)
        self.timer=QTimer(self);self.timer.setSingleShot(True);self.timer.timeout.connect(self.save);self.scene.changed.connect(self.scene_changed)
        self.load();self.loading=False
    def scene_changed(self,*_):
        if self.loading or self.refreshing:return
        self.refreshing=True
        for item in self.scene.items():
            if isinstance(item,ConnectorItem):item.update_position()
        self.refreshing=False;self.timer.start(700)
    def style_shape(self,item):
        item.setBrush(QBrush(QColor('#ffffff')));item.setPen(QPen(QColor('#18181a'),2));item.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable|QGraphicsItem.GraphicsItemFlag.ItemIsSelectable);item.setData(1,uuid.uuid4().hex);self.scene.addItem(item);item.setPos(self.view.mapToScene(self.view.viewport().rect().center())-QPointF(80,45));return item
    def rect(self):return self.style_shape(QGraphicsRectItem(0,0,160,90))
    def ellipse(self):return self.style_shape(QGraphicsEllipseItem(0,0,160,90))
    def diamond(self):return self.style_shape(QGraphicsPolygonItem(QPolygonF([QPointF(90,0),QPointF(180,55),QPointF(90,110),QPointF(0,55)])))
    def text(self):
        selected=[i for i in self.scene.selectedItems() if not isinstance(i,(QGraphicsLineItem,QGraphicsTextItem))]
        current=''
        if selected:
            children=[c for c in selected[0].childItems() if isinstance(c,QGraphicsTextItem)]
            if children:current=children[0].toPlainText()
        value,ok=QInputDialog.getText(self,'Shape text','Text',text=current)
        if not ok:return
        if selected:
            parent=selected[0];children=[c for c in parent.childItems() if isinstance(c,QGraphicsTextItem)];label=children[0] if children else QGraphicsTextItem(parent);label.setDefaultTextColor(QColor('#18181a'));label.setPlainText(value);bounds=label.boundingRect();shape=parent.boundingRect();label.setPos(shape.center().x()-bounds.width()/2,shape.center().y()-bounds.height()/2)
        elif value:
            label=QGraphicsTextItem(value);label.setDefaultTextColor(QColor('#18181a'));label.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable|QGraphicsItem.GraphicsItemFlag.ItemIsSelectable);self.scene.addItem(label);label.setPos(self.view.mapToScene(self.view.viewport().rect().center()))
    def connector(self,arrow):
        selected=[i for i in self.scene.selectedItems() if not isinstance(i,(QGraphicsLineItem,QGraphicsTextItem))]
        if len(selected)!=2:QMessageBox.information(self,'Connect shapes','Select exactly two shapes (Ctrl+click), then choose Line or Arrow.');return
        first,second=selected[0],selected[1]
        if arrow:
            a=self.shape_name(first,'Shape A');b=self.shape_name(second,'Shape B');choice,ok=QInputDialog.getItem(self,'Arrow direction','Choose the arrow direction',[f'{a}  →  {b}',f'{b}  →  {a}'],0,False)
            if not ok:return
            source,target=(first,second) if choice.startswith(a+'  →') else (second,first)
        else:source,target=first,second
        edge=ConnectorItem(source,target,arrow);self.scene.addItem(edge);edge.update_position();first.setSelected(False);second.setSelected(False);edge.setSelected(True)
    @staticmethod
    def shape_name(item,fallback):
        labels=[c.toPlainText().strip() for c in item.childItems() if isinstance(c,QGraphicsTextItem) and c.toPlainText().strip()]
        if labels:return labels[0]
        if isinstance(item,QGraphicsEllipseItem):return 'Oval'
        if isinstance(item,QGraphicsPolygonItem):return 'Diamond'
        if isinstance(item,QGraphicsRectItem):return 'Rectangle'
        return fallback
    def detach(self):
        connectors=[i for i in self.scene.selectedItems() if isinstance(i,ConnectorItem)]
        if not connectors:QMessageBox.information(self,'Detach connector','Select a line or arrow first.');return
        for edge in connectors:edge.detach()
    def delete(self):
        selected=self.scene.selectedItems()
        shapes=[i for i in selected if not isinstance(i,(ConnectorItem,QGraphicsTextItem))]
        for edge in [i for i in self.scene.items() if isinstance(i,ConnectorItem)]:
            if edge in selected or edge.source in shapes or edge.target in shapes:self.scene.removeItem(edge)
        for item in selected:
            if item.scene() is self.scene:self.scene.removeItem(item)
    def fit(self):
        bounds=self.scene.itemsBoundingRect()
        if not bounds.isEmpty():self.view.fitInView(bounds.adjusted(-60,-60,60,60),Qt.AspectRatioMode.KeepAspectRatio)
    def export_png(self):
        path,_=QFileDialog.getSaveFileName(self,'Export flowchart',self.node['name']+'.png','PNG image (*.png)')
        if not path:return
        bounds=self.scene.itemsBoundingRect().adjusted(-40,-40,40,40)
        if bounds.isEmpty():QMessageBox.information(self,'Empty flowchart','Add a shape before exporting.');return
        image=QImage(max(1,int(bounds.width())),max(1,int(bounds.height())),QImage.Format.Format_ARGB32);image.fill(QColor('white'));p=QPainter(image);self.scene.render(p,QRectF(image.rect()),bounds);p.end();image.save(path)
    def save(self):
        if self.loading:return
        data=[]
        for item in self.scene.items():
            if item.parentItem() is not None:continue
            base={'x':item.x(),'y':item.y()}
            if isinstance(item,QGraphicsTextItem):base.update(kind='text',text=item.toPlainText())
            elif isinstance(item,ConnectorItem):base.update(kind='arrow' if item.arrow else 'line',line=[item.line().x1(),item.line().y1(),item.line().x2(),item.line().y2()],source=item.source.data(1) if item.source else None,target=item.target.data(1) if item.target else None)
            elif isinstance(item,QGraphicsEllipseItem):base.update(kind='ellipse',rect=[item.rect().x(),item.rect().y(),item.rect().width(),item.rect().height()])
            elif isinstance(item,QGraphicsPolygonItem):base.update(kind='diamond',points=[[p.x(),p.y()] for p in item.polygon()])
            elif isinstance(item,QGraphicsRectItem):base.update(kind='rect',rect=[item.rect().x(),item.rect().y(),item.rect().width(),item.rect().height()])
            else:continue
            if not isinstance(item,(ConnectorItem,QGraphicsTextItem)):base['uid']=item.data(1)
            children=[c for c in item.childItems() if isinstance(c,QGraphicsTextItem)]
            if children:base['label']=children[0].toPlainText()
            data.append(base)
        self.db.save_subpage(self.node['id'],{'content':json.dumps({'version':2,'items':data}),'tags':{}})
    def load(self):
        dump=self.db.load_subpage(self.node['id']) or {}
        try:
            if isinstance(dump,dict) and dump.get('items') is not None:state=dump
            else:
                raw=dump.get('content','') if isinstance(dump,dict) else dump
                state=json.loads(raw) if raw else {}
            data=state.get('items',state if isinstance(state,list) else [])
        except Exception:data=[]
        pending_edges=[];nodes={}
        for obj in data:
            kind=obj.get('kind') or obj.get('type')
            if kind in ('line','arrow'):
                pending_edges.append(obj);continue
            elif kind=='text':item=QGraphicsTextItem(obj.get('text',''));item.setDefaultTextColor(QColor('#18181a'));item.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable|QGraphicsItem.GraphicsItemFlag.ItemIsSelectable);self.scene.addItem(item)
            else:
                legacy=obj.get('coords') or []
                rect=obj.get('rect') or (legacy[:4] if len(legacy)==4 else [0,0,160,90])
                if kind in ('ellipse','oval'):item=QGraphicsEllipseItem(*rect)
                elif kind in ('diamond','polygon'):
                    points=obj.get('points')
                    if not points and len(legacy)>=8:points=[legacy[i:i+2] for i in range(0,len(legacy),2)]
                    item=QGraphicsPolygonItem(QPolygonF([QPointF(*p) for p in (points or [[90,0],[180,55],[90,110],[0,55]])]))
                else:item=QGraphicsRectItem(*rect)
                self.style_shape(item)
                item.setData(1,obj.get('uid') or uuid.uuid4().hex);nodes[item.data(1)]=item
                label_text=obj.get('label') or obj.get('text')
                if label_text:
                    label=QGraphicsTextItem(label_text,item);label.setDefaultTextColor(QColor('#18181a'));label.setPos(item.boundingRect().center()-label.boundingRect().center())
            item.setPos(obj.get('x',0),obj.get('y',0))
        for obj in pending_edges:
            points=obj.get('line') or obj.get('coords',[0,0,100,100]);actual='arrow' if obj.get('arrow') else obj.get('kind','line');edge=ConnectorItem(nodes.get(obj.get('source')),nodes.get(obj.get('target')),actual=='arrow',QLineF(*points));self.scene.addItem(edge);edge.update_position()


class PlannerPage(QWidget):
    def __init__(self, db):
        super().__init__(); self.db=db
        layout=QHBoxLayout(self); layout.setContentsMargins(24,24,24,24); layout.setSpacing(22)
        self.calendar=QCalendarWidget(); self.calendar.setGridVisible(False); layout.addWidget(self.calendar,1)
        right=QWidget(); r=QVBoxLayout(right); r.setContentsMargins(0,0,0,0)
        self.heading=QLabel(objectName='pageTitle'); r.addWidget(self.heading)
        entry_row=QHBoxLayout(); self.input=QLineEdit(placeholderText='Add a task…'); self.projects=QComboBox(); self.add=button('Add',self.add_task,'primary')
        entry_row.addWidget(self.input,1); entry_row.addWidget(self.projects); entry_row.addWidget(self.add); r.addLayout(entry_row)
        self.list=QListWidget(); r.addWidget(self.list,1); layout.addWidget(right,2)
        self.calendar.selectionChanged.connect(self.refresh); self.input.returnPressed.connect(self.add_task); self.list.itemClicked.connect(self.toggle_clicked)
        self.reload_projects(); self.refresh()
    def reload_projects(self):
        self.projects.clear(); self.projects.addItem('No project',None)
        for p in self.db.get_all_projects(): self.projects.addItem(p['title'],p['id'])
    def refresh(self):
        day=self.calendar.selectedDate(); self.heading.setText(day.toString('dddd, d MMMM yyyy')); self.list.blockSignals(True); self.list.clear()
        for task in self.db.get_tasks(day.toString('yyyy-MM-dd')):
            label=task['title']+(f"  ·  {task['project_title']}" if task.get('project_title') else '')
            item=QListWidgetItem(label); item.setData(Qt.ItemDataRole.UserRole,task['id']); item.setCheckState(Qt.CheckState.Checked if task['completed'] else Qt.CheckState.Unchecked); item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable); self.list.addItem(item)
        self.list.blockSignals(False)
    def add_task(self):
        title=self.input.text().strip()
        if title: self.db.add_task(self.calendar.selectedDate().toString('yyyy-MM-dd'),title,self.projects.currentData()); self.input.clear(); self.refresh()
    def toggle_clicked(self,item):
        checked=item.checkState()!=Qt.CheckState.Checked;item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked);self.db.set_task_completed(item.data(Qt.ItemDataRole.UserRole),checked)


class DiaryPage(QWidget):
    PASSWORD_SETTING = 'diary_password_v2'
    def __init__(self, db, parent=None):
        super().__init__(parent); self.db=db; self.unlocked=False
        layout=QVBoxLayout(self); layout.setContentsMargins(44,30,44,28)
        top=QHBoxLayout(); top.addWidget(QLabel('Private diary',objectName='pageTitle')); top.addStretch(); self.day=QDateEdit(QDate.currentDate()); self.day.setCalendarPopup(True); top.addWidget(self.day); layout.addLayout(top)
        layout.addWidget(QLabel('An additional password protects entries stored in your encrypted vault.',objectName='muted'))
        self.edit=QTextEdit(); self.edit.setPlaceholderText('Unlock the diary to begin…'); self.edit.setEnabled(False); layout.addWidget(self.edit,1)
        row=QHBoxLayout(); self.state=QLabel(objectName='muted'); row.addWidget(self.state); row.addStretch(); row.addWidget(button('Unlock',self.unlock)); row.addWidget(button('Save entry',self.save,'primary')); layout.addLayout(row)
        self.day.dateChanged.connect(self.load)
    def unlock(self):
        import hashlib,hmac
        stored=self.db.get_setting(self.PASSWORD_SETTING)
        if not stored:
            password,ok=QInputDialog.getText(self,'Create diary password','Create a new password used only for your private diary',QLineEdit.EchoMode.Password)
            if not ok:return
            if len(password) < 6:
                QMessageBox.warning(self,'Password too short','Use at least 6 characters for the separate diary password.');return
            confirm,confirmed=QInputDialog.getText(self,'Confirm diary password','Enter the new diary password again',QLineEdit.EchoMode.Password)
            if not confirmed or confirm != password:
                QMessageBox.warning(self,'Passwords do not match','The diary passwords did not match.');return
            salt=os.urandom(16); digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,240000); self.db.set_setting(self.PASSWORD_SETTING,salt.hex()+':'+digest.hex()); valid=True
        else:
            password,ok=QInputDialog.getText(self,'Unlock diary','Diary password',QLineEdit.EchoMode.Password)
            if not ok:return
            salt,digest=stored.split(':',1); valid=hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),240000).hex(),digest)
        if not valid: QMessageBox.warning(self,'Access denied','Incorrect diary password.'); return
        self.unlocked=True; self.edit.setEnabled(True); self.load()
    def lock(self):
        if self.unlocked:
            self.save()
        self.unlocked=False;self.edit.clear();self.edit.setEnabled(False);self.edit.setPlaceholderText('Unlock the diary to begin…');self.state.setText('Locked')
    def load(self):
        if self.unlocked: self.edit.setPlainText(self.db.load_diary_entry(self.day.date().toString('yyyy-MM-dd'))); self.state.setText('Unlocked')
    def save(self):
        if self.unlocked: self.db.save_diary_entry(self.day.date().toString('yyyy-MM-dd'),self.edit.toPlainText()); self.state.setText('Saved')


class Workspace(QMainWindow):
    def __init__(self, auth_manager):
        super().__init__(); self.auth_manager=auth_manager; self.db=get_db(); self.current_project=None; self.open_editors={}
        self.setWindowTitle('Tarizz'); self.resize(1380,840); self.setMinimumSize(1050,650); self.setStyleSheet(STYLE)
        root=QWidget(objectName='root'); self.setCentralWidget(root); layout=QHBoxLayout(root); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
        self.rail=QFrame(objectName='rail'); rail=QVBoxLayout(self.rail); rail.setContentsMargins(6,10,6,10); rail.setSpacing(3)
        logo=QLabel('T'); logo.setAlignment(Qt.AlignmentFlag.AlignCenter); logo.setStyleSheet('font-size:19px;font-weight:800;color:#a99cff;padding:10px'); rail.addWidget(logo)
        for icon,tip,fn in [('⌂','Projects',self.show_home),('▦','Calendar & tasks',self.show_planner),('◈','Private diary',self.show_diary)]:
            b=button(icon,fn,'railButton'); b.setToolTip(tip); rail.addWidget(b)
        rail.addStretch(); layout.addWidget(self.rail)
        self.sidebar=QFrame(objectName='sidebar'); side=QVBoxLayout(self.sidebar); side.setContentsMargins(12,16,12,12)
        side.addWidget(QLabel('TARIZZ',objectName='brand')); side.addWidget(QLabel('EXPLORER',objectName='eyebrow'))
        self.search=QLineEdit(placeholderText='Search projects and notes'); self.search.textChanged.connect(self.filter_tree); side.addWidget(self.search)
        self.tree=QTreeWidget(); self.tree.setHeaderHidden(True); self.tree.itemDoubleClicked.connect(self.open_tree_item); self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu); self.tree.customContextMenuRequested.connect(self.tree_menu); side.addWidget(self.tree,1)
        addrow=QHBoxLayout(); addrow.addWidget(button('＋ Note',lambda:self.add_node('subpage'))); addrow.addWidget(button('＋ Folder',lambda:self.add_node('folder'))); side.addLayout(addrow)
        layout.addWidget(self.sidebar); self.sidebar.setFixedWidth(280)
        self.tabs=QTabWidget(); self.tabs.setTabsClosable(True); self.tabs.tabCloseRequested.connect(self.close_tab); layout.addWidget(self.tabs,1)
        self.home=self.build_home(); self.planner=PlannerPage(self.db); self.diary=DiaryPage(self.db,self)
        self.tabs.addTab(self.home,'Projects'); self.load_projects(); self.statusBar().showMessage('Ready')

    def build_home(self):
        page=QWidget(); box=QVBoxLayout(page); box.setContentsMargins(38,30,38,30)
        title=QLabel('Projects',objectName='pageTitle'); box.addWidget(title); box.addWidget(QLabel('Your private workspace',objectName='muted'))
        tools=QHBoxLayout(); tools.addWidget(button('＋ New project',self.new_project,'primary')); tools.addWidget(button('Import',self.import_project)); tools.addWidget(button('Export',self.export_menu)); tools.addWidget(button('Delete',self.delete_project,'danger')); tools.addStretch(); box.addLayout(tools)
        self.projects=QListWidget(); self.projects.itemDoubleClicked.connect(self.select_project); self.projects.itemSelectionChanged.connect(self.project_selection_changed); box.addWidget(self.projects,1); return page
    def show_home(self): self.tabs.setCurrentWidget(self.home)
    def show_planner(self):
        self.planner.reload_projects(); self.open_fixed(self.planner,'Calendar')
    def show_diary(self): self.open_fixed(self.diary,'Private diary')
    def open_fixed(self,widget,title):
        i=self.tabs.indexOf(widget)
        if i<0:i=self.tabs.addTab(widget,title)
        self.tabs.setCurrentIndex(i)
    def load_projects(self):
        self.projects.clear()
        for p in self.db.get_all_projects(): item=QListWidgetItem(f"{p['title']}\n{p.get('description') or 'No description'}"); item.setData(Qt.ItemDataRole.UserRole,p); item.setSizeHint(item.sizeHint().expandedTo(item.sizeHint())); self.projects.addItem(item)
    def new_project(self):
        title,ok=QInputDialog.getText(self,'New project','Project name')
        if ok and title.strip(): self.db.create_project(title.strip(),'New workspace',len(self.db.get_all_projects())); self.load_projects(); self.planner.reload_projects()
    def select_project(self,item): self.current_project=item.data(Qt.ItemDataRole.UserRole); self.load_tree(); self.statusBar().showMessage(f"Opened {self.current_project['title']}")
    def project_selection_changed(self):
        items=self.projects.selectedItems()
        if items:self.current_project=items[0].data(Qt.ItemDataRole.UserRole);self.load_tree()
    def delete_project(self):
        if not self.current_project:return
        if QMessageBox.question(self,'Delete project',f"Delete '{self.current_project['title']}' and all its content?")==QMessageBox.StandardButton.Yes:
            self.db.delete_project(self.current_project['id']);self.current_project=None;self.tree.clear();self.load_projects();self.planner.reload_projects()
    def export_menu(self):
        if not self.current_project:QMessageBox.information(self,'Select a project','Select a project to export.');return
        menu=QMenu(self);menu.addAction('Tarizz package',self.export_package);menu.addAction('Plain text',self.export_text);menu.addAction('PDF',self.export_pdf)
        menu.exec(self.cursor().pos())
    def export_package(self):
        path,_=QFileDialog.getSaveFileName(self,'Export project',self.current_project['title']+'.tarizz','Tarizz project (*.tarizz)')
        if path:
            from project_archive import export_project_package
            try:export_project_package(self.current_project['id'],path,self.db);self.statusBar().showMessage('Project exported')
            except Exception as exc:QMessageBox.critical(self,'Export failed',str(exc))
    def export_text(self):
        path,_=QFileDialog.getSaveFileName(self,'Export text',self.current_project['title']+'.txt','Text files (*.txt)')
        if not path:return
        nodes=self.db.get_all_nodes_for_project(self.current_project['id']);children={}
        for node in nodes:children.setdefault(node['parent_id'],[]).append(node)
        lines=[self.current_project['title'],'='*len(self.current_project['title']),'']
        def walk(parent,depth=0):
            for node in children.get(parent,[]):
                lines.append('  '*depth+node['name'])
                if node['node_type']=='subpage':
                    dump=self.db.load_subpage(node['id']) or {};content=dump if isinstance(dump,str) else dump.get('content','');lines.extend('  '*(depth+1)+line for line in content.splitlines());lines.append('')
                walk(node['id'],depth+1)
        walk(None)
        try:
            with open(path,'w',encoding='utf-8') as stream:stream.write('\n'.join(lines))
            self.statusBar().showMessage('Text exported')
        except OSError as exc:QMessageBox.critical(self,'Export failed',str(exc))
    def export_pdf(self):
        path,_=QFileDialog.getSaveFileName(self,'Export PDF',self.current_project['title']+'.pdf','PDF files (*.pdf)')
        if not path:return
        try:
            import backend.database as database
            from project_export import ProjectExporter
            ProjectExporter(self.current_project['id'],self.current_project['title'],database).export_to_pdf(path);self.statusBar().showMessage('PDF exported')
        except Exception as exc:QMessageBox.critical(self,'Export failed',str(exc))
    def load_tree(self):
        self.tree.clear()
        if not self.current_project:return
        root=QTreeWidgetItem([self.current_project['title']]); root.setData(0,Qt.ItemDataRole.UserRole,{'root':True}); self.tree.addTopLevelItem(root)
        nodes=self.db.get_all_nodes_for_project(self.current_project['id']); mapping={None:root}
        pending=list(nodes)
        while pending:
            progressed=False
            for node in pending[:]:
                if node['parent_id'] in mapping:
                    icon={'folder':'▸','subpage':'□','flowchart':'◇'}[node['node_type']]; child=QTreeWidgetItem([f"{icon}  {node['name']}"]); child.setData(0,Qt.ItemDataRole.UserRole,node); mapping[node['id']]=child; mapping[node['parent_id']].addChild(child); pending.remove(node); progressed=True
            if not progressed:break
        root.setExpanded(True)
    def filter_tree(self,value):
        term=value.lower()
        it=self.tree.invisibleRootItem()
        def visit(node):
            visible=term in node.text(0).lower()
            for i in range(node.childCount()): visible=visit(node.child(i)) or visible
            node.setHidden(not visible); return visible
        for i in range(it.childCount()):visit(it.child(i))
    def selected_parent(self):
        item=self.tree.currentItem(); data=item.data(0,Qt.ItemDataRole.UserRole) if item else None
        if not data or data.get('root'):return None
        return data['id'] if data['node_type']=='folder' else data.get('parent_id')
    def add_node(self,kind):
        if not self.current_project: QMessageBox.information(self,'Select a project','Open a project first.'); return
        name,ok=QInputDialog.getText(self,f'New {kind}', 'Name')
        if ok and name.strip(): self.db.create_node(self.current_project['id'],self.selected_parent(),kind,name.strip()); self.load_tree()
    def tree_menu(self,pos):
        menu=QMenu(self); menu.addAction('New note',lambda:self.add_node('subpage')); menu.addAction('New folder',lambda:self.add_node('folder')); menu.addAction('New flowchart',lambda:self.add_node('flowchart'))
        item=self.tree.itemAt(pos)
        if item and item.data(0,Qt.ItemDataRole.UserRole) and not item.data(0,Qt.ItemDataRole.UserRole).get('root'): menu.addSeparator(); menu.addAction('Rename',lambda:self.rename_node(item)); menu.addAction('Delete',lambda:self.delete_node(item))
        menu.exec(self.tree.viewport().mapToGlobal(pos))
    def rename_node(self,item):
        node=item.data(0,Qt.ItemDataRole.UserRole); name,ok=QInputDialog.getText(self,'Rename','Name',text=node['name'])
        if ok and name.strip():self.db.rename_node(node['id'],name.strip());self.load_tree()
    def delete_node(self,item):
        node=item.data(0,Qt.ItemDataRole.UserRole)
        if QMessageBox.question(self,'Delete',f"Delete '{node['name']}' and its contents?")==QMessageBox.StandardButton.Yes:self.db.delete_node(node['id']);self.load_tree()
    def open_tree_item(self,item,column=0):
        node=item.data(0,Qt.ItemDataRole.UserRole)
        if not node or node.get('root') or node['node_type']=='folder':return
        if node['id'] in self.open_editors:self.tabs.setCurrentWidget(self.open_editors[node['id']]);return
        page=FlowchartPage(self.db,node) if node['node_type']=='flowchart' else RichEditor(self.db,node,self)
        self.open_editors[node['id']]=page; self.tabs.setCurrentIndex(self.tabs.addTab(page,node['name']))
    def close_tab(self,index):
        widget=self.tabs.widget(index)
        if widget is self.home:return
        if hasattr(widget,'save'):widget.save()
        for key,value in list(self.open_editors.items()):
            if value is widget:del self.open_editors[key]
        self.tabs.removeTab(index)
    def import_project(self):
        path,_=QFileDialog.getOpenFileName(self,'Import project','','Tarizz project (*.tarizz)')
        if path:
            try:
                from project_archive import import_project_package
                import_project_package(path,self.db);self.load_projects()
            except Exception as exc:QMessageBox.critical(self,'Import failed',str(exc))
    def closeEvent(self,event):
        for editor in self.open_editors.values():
            if hasattr(editor,'save'):editor.save()
        self.diary.save(); event.accept()


def run_qt_app(auth_manager):
    app=QApplication.instance() or QApplication([]); app.setApplicationName('Tarizz'); app.setStyle('Fusion')
    window=Workspace(auth_manager); window.show(); return app.exec()
