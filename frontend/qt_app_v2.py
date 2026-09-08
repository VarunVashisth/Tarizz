"""Tarizz editorial single-window interface inspired by varunvashisth.in."""
from datetime import date

from PyQt6.QtCore import QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QFont, QKeySequence, QPainter, QPalette, QPen
from PyQt6.QtWidgets import (
    QApplication, QAbstractItemView, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QListView, QListWidget, QListWidgetItem,
    QMainWindow, QMenu, QMessageBox, QPushButton, QScrollArea, QSizePolicy,
    QSplitter, QStackedWidget, QStyledItemDelegate, QStyle, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

from backend.database import get_db
from qt_app import DiaryPage, FlowchartPage, PlannerPage, RichEditor


LIGHT = {
    'bg':'#fbfbfd','surface':'#ffffff','soft':'#f3f3f7','text':'#15151a','muted':'#686873',
    'faint':'#9898a4','border':'#e5e5ec','primary':'#17171c','on_primary':'#ffffff','hover':'#f0f0f5',
    'accent':'#6857e5','accent_hover':'#5847d4','accent_soft':'#eeebff','accent_text':'#4938bd',
    'coral':'#e76f51','success':'#238b65','danger':'#c94747','danger_soft':'#fff0f0','editor':'#ffffff'
}
DARK = {
    'bg':'#0e0e11','surface':'#151519','soft':'#1d1d23','text':'#f4f3f8','muted':'#a09faa',
    'faint':'#6f6e79','border':'#2a2932','primary':'#f5f4f8','on_primary':'#141419','hover':'#24232b',
    'accent':'#9587ff','accent_hover':'#aa9fff','accent_soft':'#28233f','accent_text':'#b8afff',
    'coral':'#ff8a6b','success':'#57c99c','danger':'#ff7a7a','danger_soft':'#382123','editor':'#111115'
}


def stylesheet(c):
    return f"""
    * {{ font-family:'Geist','Inter','Segoe UI',sans-serif; font-size:13px; color:{c['text']}; }}
    QMainWindow, QWidget#page, QStackedWidget {{ background:{c['bg']}; }}
    QDialog, QMessageBox, QInputDialog, QFileDialog {{ background:{c['bg']}; color:{c['text']}; }}
    QDialog QLabel, QMessageBox QLabel, QInputDialog QLabel, QFileDialog QLabel {{ background:transparent; color:{c['text']}; }}
    QDialog QLineEdit, QInputDialog QLineEdit {{ background:{c['surface']}; color:{c['text']}; border:1px solid {c['border']}; selection-background-color:{c['muted']}; }}
    QDialog QPushButton, QMessageBox QPushButton, QInputDialog QPushButton, QFileDialog QPushButton {{ background:{c['surface']}; color:{c['text']}; border:1px solid {c['border']}; min-width:72px; }}
    QDialog QPushButton:hover, QMessageBox QPushButton:hover, QInputDialog QPushButton:hover {{ background:{c['hover']}; }}
    QFrame#topbar {{ background:{c['surface']}; border-bottom:1px solid {c['border']}; }}
    QFrame#navPill {{ background:{c['soft']}; border:1px solid {c['border']}; border-radius:9px; }}
    QFrame#panel {{ background:{c['surface']}; border:1px solid {c['border']}; border-radius:12px; }}
    QFrame#projectSidebar {{ background:{c['surface']}; border-right:1px solid {c['border']}; }}
    QFrame#projectHeader {{ background:{c['surface']}; border-bottom:1px solid {c['border']}; }}
    QLabel#brand {{ font-family:'Marcellus','Georgia',serif; font-size:18px; font-weight:700; letter-spacing:2px; }}
    QLabel#hero {{ font-size:38px; font-weight:800; letter-spacing:-1.2px; }}
    QLabel#title, QLabel#pageTitle {{ font-size:24px; font-weight:750; letter-spacing:-.3px; }}
    QLabel#emptyTitle {{ font-size:18px; font-weight:700; }}
    QLabel#welcomeIcon {{ color:{c['accent']}; background:{c['accent_soft']}; border-radius:18px; padding:14px; font-size:24px; }}
    QLabel#eyebrow {{ color:{c['faint']}; font-size:10px; font-weight:650; letter-spacing:1px; }}
    QLabel#muted {{ color:{c['muted']}; }}
    QLabel#badge {{ color:{c['accent_text']}; background:{c['accent_soft']}; border:1px solid {c['accent_soft']}; border-radius:9px; padding:4px 8px; font-size:11px; font-weight:650; }}
    QPushButton {{ background:transparent; border:1px solid transparent; border-radius:7px; padding:9px 13px; font-weight:500; }}
    QPushButton:hover {{ background:{c['hover']}; }}
    QPushButton#icon {{ font-size:17px; padding:7px; min-width:20px; }}
    QPushButton#outline {{ border:1px solid {c['border']}; }}
    QPushButton#quiet {{ color:{c['muted']}; }}
    QPushButton#danger {{ color:{c['danger']}; }} QPushButton#danger:hover {{ background:{c['danger_soft']}; }}
    QPushButton#primary {{ background:{c['primary']}; color:{c['on_primary']}; border:1px solid {c['primary']}; font-weight:650; padding:10px 16px; }}
    QPushButton#primary:hover {{ background:{c['accent']}; border-color:{c['accent']}; color:#ffffff; }}
    QPushButton#navButton {{ padding:7px 13px; color:{c['muted']}; border-radius:6px; }}
    QPushButton#navButton:hover {{ color:{c['text']}; background:{c['surface']}; }}
    QPushButton#navButton[active="true"] {{ color:{c['accent_text']}; background:{c['surface']}; border:1px solid {c['border']}; font-weight:650; }}
    QLineEdit {{ background:{c['surface']}; border:1px solid {c['border']}; border-radius:8px; padding:10px 13px; selection-background-color:{c['accent']}; }}
    QLineEdit:focus {{ border:1px solid {c['accent']}; }}
    QComboBox, QDateEdit {{ background:{c['bg']}; color:{c['text']}; border:1px solid {c['border']}; border-radius:6px; padding:8px 10px; }}
    QComboBox QAbstractItemView {{ background:{c['bg']}; color:{c['text']}; selection-background-color:{c['soft']}; }}
    QMenu {{ background:{c['surface']}; color:{c['text']}; border:1px solid {c['border']}; border-radius:8px; padding:6px; }}
    QMenu::item {{ padding:8px 25px; border-radius:5px; }} QMenu::item:selected {{ background:{c['accent_soft']}; color:{c['accent_text']}; }}
    QFrame#editorHeader {{ background:{c['editor']}; color:{c['text']}; border-bottom:1px solid {c['border']}; }}
    QFrame#status {{ background:{c['surface']}; color:{c['text']}; border-top:1px solid {c['border']}; }}
    QListWidget {{ background:{c['bg']}; color:{c['text']}; border:1px solid {c['border']}; outline:0; }}
    QListWidget::item {{ color:{c['text']}; padding:7px; }} QListWidget::item:selected {{ background:{c['soft']}; color:{c['text']}; }}
    QListWidget::indicator {{ width:15px; height:15px; border:1px solid {c['faint']}; border-radius:4px; background:{c['surface']}; }}
    QListWidget::indicator:checked {{ background:{c['accent']}; border-color:{c['accent']}; }}
    QListWidget#cards {{ background:{c['bg']}; border:0; outline:0; }}
    QListWidget#cards::item {{ background:{c['surface']}; border:1px solid {c['border']}; border-radius:11px; padding:22px; margin:7px; }}
    QListWidget#cards::item:hover {{ background:{c['soft']}; border-color:{c['faint']}; }}
    QListWidget#cards::item:selected {{ background:{c['text']}; color:{c['bg']}; border-color:{c['text']}; }}
    QTreeWidget {{ background:{c['surface']}; border:0; outline:0; padding:7px; }}
    QTreeWidget::item {{ padding:8px 7px; border-radius:6px; }}
    QTreeWidget::item:hover {{ background:{c['hover']}; }}
    QTreeWidget::item:selected {{ background:{c['accent_soft']}; color:{c['accent_text']}; }}
    QTabWidget::pane {{ border:0; background:{c['bg']}; }}
    QTabBar::tab {{ background:{c['surface']}; border-right:1px solid {c['border']}; border-bottom:1px solid {c['border']}; padding:10px 18px; color:{c['muted']}; }}
    QTabBar::tab:hover {{ background:{c['hover']}; color:{c['text']}; }}
    QTabBar::tab:selected {{ background:{c['editor']}; color:{c['text']}; border-top:2px solid {c['accent']}; border-bottom-color:{c['editor']}; }}
    QTextEdit, QTextBrowser {{ background:{c['editor']}; color:{c['text']}; border:0; padding:34px 68px; selection-background-color:{c['accent']}; selection-color:#ffffff; }}
    QTextEdit:disabled {{ background:{c['soft']}; color:{c['faint']}; }}
    QToolBar {{ background:{c['surface']}; border:0; border-bottom:1px solid {c['border']}; padding:5px 12px; spacing:2px; }}
    QToolButton {{ background:transparent; border:0; border-radius:4px; padding:6px 8px; }}
    QToolButton:hover {{ background:{c['accent_soft']}; color:{c['accent_text']}; }}
    QCalendarWidget QWidget {{ background:{c['bg']}; color:{c['text']}; alternate-background-color:{c['surface']}; }}
    QCalendarWidget QAbstractItemView {{ background:{c['bg']}; color:{c['text']}; selection-background-color:{c['accent']}; selection-color:#ffffff; outline:0; }}
    QCalendarWidget QToolButton {{ color:{c['text']}; background:transparent; border-radius:5px; padding:6px; }}
    QSplitter::handle {{ background:{c['border']}; width:1px; }} QSplitter::handle:hover {{ background:{c['accent']}; }}
    QScrollBar:vertical {{ background:transparent; width:9px; }} QScrollBar::handle:vertical {{ background:{c['border']}; border-radius:4px; min-height:30px; }}
    """


def btn(text, fn=None, kind=None, tip=None):
    b=QPushButton(text); b.setObjectName(kind or ''); b.setCursor(Qt.CursorShape.PointingHandCursor)
    if fn:b.clicked.connect(fn)
    if tip:b.setToolTip(tip)
    return b


class ReorderableCardList(QListWidget):
    """A card grid whose drop always becomes a stable model reorder."""
    orderChanged=pyqtSignal()
    def paintEvent(self,event):
        super().paintEvent(event)
        if self.count():return
        c=DARK if getattr(self.window(),'dark',False) else LIGHT;p=QPainter(self.viewport());p.setRenderHint(QPainter.RenderHint.Antialiasing)
        area=QRectF(self.viewport().rect()).adjusted(28,28,-28,-28);p.setPen(QPen(QColor(c['border']),1,Qt.PenStyle.DashLine));p.setBrush(QColor(c['surface']));p.drawRoundedRect(area,14,14)
        title=QFont('Geist');title.setPixelSize(19);title.setWeight(QFont.Weight.DemiBold);p.setFont(title);p.setPen(QColor(c['text']));p.drawText(area.adjusted(20,0,-20,-24),Qt.AlignmentFlag.AlignCenter,'Your first project starts here')
        body=QFont('Geist');body.setPixelSize(12);p.setFont(body);p.setPen(QColor(c['muted']));p.drawText(area.adjusted(20,42,-20,0),Qt.AlignmentFlag.AlignCenter,'Create a project to collect notes, files and flowcharts.')
    def dropEvent(self,event):
        source=self.currentRow()
        if source < 0:return super().dropEvent(event)
        target=self.indexAt(event.position().toPoint()).row()
        if target < 0:target=self.count()-1
        if target != source:
            item=self.takeItem(source)
            if source < target:target-=1
            self.insertItem(max(0,target),item);self.setCurrentItem(item)
            self.orderChanged.emit()
        event.acceptProposedAction()


class ProjectCardDelegate(QStyledItemDelegate):
    """Editorial project cards with predictable contrast in both themes."""
    ACCENTS=('#6857e5','#e76f51','#238b65','#3b82c4','#a855a5')
    def sizeHint(self,option,index):return QSize(326,192)
    def paint(self,painter,option,index):
        painter.save();p=index.data(Qt.ItemDataRole.UserRole) or {};window=option.widget.window();c=DARK if getattr(window,'dark',False) else LIGHT
        selected=bool(option.state & QStyle.StateFlag.State_Selected);hovered=bool(option.state & QStyle.StateFlag.State_MouseOver)
        accent=QColor(self.ACCENTS[index.row()%len(self.ACCENTS)]);bg=c['accent_soft'] if selected else c['soft'] if hovered else c['surface'];fg=c['text'];muted=c['muted'];border=accent.name() if selected else c['faint'] if hovered else c['border']
        rect=QRectF(option.rect.adjusted(7,7,-7,-7));painter.setRenderHint(QPainter.RenderHint.Antialiasing);painter.setBrush(QColor(bg));painter.setPen(QPen(QColor(border),1.2 if selected else 1));painter.drawRoundedRect(rect,12,12)
        painter.setPen(Qt.PenStyle.NoPen);painter.setBrush(accent);painter.drawRoundedRect(QRectF(rect.left()+16,rect.top()+15,34,4),2,2)
        left=rect.left()+20;top=rect.top()+29;right=rect.right()-20
        font=QFont('Geist');font.setPixelSize(9);font.setWeight(QFont.Weight.DemiBold);font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing,1.15);painter.setFont(font);painter.setPen(QColor(muted));painter.drawText(QRectF(left,top,right-left,18),Qt.AlignmentFlag.AlignLeft,f"PROJECT {index.row()+1:02d}   ·   {p.get('node_count',0)} ITEMS")
        font.setPixelSize(18);font.setWeight(QFont.Weight.Bold);font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing,-.2);painter.setFont(font);painter.setPen(QColor(fg));painter.drawText(QRectF(left,top+29,right-left,28),Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter,p.get('title','Untitled'))
        font.setPixelSize(12);font.setWeight(QFont.Weight.Normal);font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing,0);painter.setFont(font);painter.setPen(QColor(muted));desc=p.get('description') or 'A quiet place for your next idea.';painter.drawText(QRectF(left,top+64,right-left,40),Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop|Qt.TextFlag.TextWordWrap,desc)
        painter.setPen(QPen(QColor(c['border']),1));painter.drawLine(int(left),int(rect.bottom()-39),int(right),int(rect.bottom()-39))
        font.setPixelSize(10);font.setWeight(QFont.Weight.DemiBold);painter.setFont(font);painter.setPen(accent if selected or hovered else QColor(fg));painter.drawText(QRectF(left,rect.bottom()-30,right-left,18),Qt.AlignmentFlag.AlignLeft,'OPEN WORKSPACE');painter.drawText(QRectF(left,rect.bottom()-30,right-left,18),Qt.AlignmentFlag.AlignRight,'↗');painter.restore()


class UtilityCard(QPushButton):
    """A spacious dashboard shortcut with proper title/description hierarchy."""
    def __init__(self,title,description,accent_index,callback):
        super().__init__();self.title,self.description,self.accent_index=title,description,accent_index;self.clicked.connect(callback);self.setCursor(Qt.CursorShape.PointingHandCursor);self.setMinimumHeight(80);self.setMouseTracking(True)
    def paintEvent(self,event):
        c=DARK if getattr(self.window(),'dark',False) else LIGHT;accent=QColor(ProjectCardDelegate.ACCENTS[self.accent_index%len(ProjectCardDelegate.ACCENTS)]);hovered=self.underMouse();rect=QRectF(self.rect()).adjusted(1,1,-1,-1);p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.setBrush(QColor(c['accent_soft'] if hovered else c['surface']));p.setPen(QPen(accent if hovered or self.hasFocus() else QColor(c['border']),1.2));p.drawRoundedRect(rect,11,11)
        p.setPen(Qt.PenStyle.NoPen);p.setBrush(accent);p.drawRoundedRect(QRectF(18,20,4,40),2,2);left=36
        font=QFont('Geist');font.setPixelSize(15);font.setWeight(QFont.Weight.DemiBold);p.setFont(font);p.setPen(QColor(c['text']));p.drawText(QRectF(left,16,rect.width()-95,25),Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter,self.title)
        font.setPixelSize(12);font.setWeight(QFont.Weight.Normal);p.setFont(font);p.setPen(QColor(c['muted']));p.drawText(QRectF(left,42,rect.width()-95,22),Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter,self.description)
        p.setPen(QPen(accent,1.5));p.setBrush(Qt.BrushStyle.NoBrush);p.drawEllipse(QRectF(rect.right()-48,24,30,30));p.drawText(QRectF(rect.right()-48,24,30,30),Qt.AlignmentFlag.AlignCenter,'→')


class DashboardPage(QWidget):
    openProject=pyqtSignal(dict); openCalendar=pyqtSignal(); openDiary=pyqtSignal()
    def __init__(self,db):
        super().__init__();self.setObjectName('page');self.db=db
        outer=QVBoxLayout(self);outer.setContentsMargins(60,42,60,38);outer.setSpacing(18)
        eyebrow=QLabel(date.today().strftime('%A, %d %B').upper()+'   //   PRIVATE WORKSPACE',objectName='eyebrow');outer.addWidget(eyebrow)
        top=QHBoxLayout();head=QVBoxLayout();head.setSpacing(5);head.addWidget(QLabel('Your projects.',objectName='hero'));head.addWidget(QLabel('Ideas, plans and documentation—together in one calm workspace.',objectName='muted'));top.addLayout(head);top.addStretch();top.addWidget(btn('＋  New project',self.new_project,'primary'));outer.addLayout(top)
        utilities=QHBoxLayout();utilities.setSpacing(12);utilities.addWidget(UtilityCard('Calendar & tasks','Plan the work in front of you',0,self.openCalendar.emit),1);utilities.addWidget(UtilityCard('Private diary','Write behind a second password',1,self.openDiary.emit),1);outer.addLayout(utilities)
        row=QHBoxLayout();self.search=QLineEdit(placeholderText='⌕  Search projects');self.search.setMaximumWidth(360);self.search.setClearButtonEnabled(True);self.search.textChanged.connect(self.filter);row.addWidget(self.search);row.addStretch();row.addWidget(btn('Import',self.import_project,'quiet'));row.addWidget(btn('Export',self.export_menu,'outline'));row.addWidget(btn('Delete',self.delete_selected,'danger'));outer.addLayout(row)
        collection=QHBoxLayout();collection.addWidget(QLabel('PROJECT COLLECTION',objectName='eyebrow'));collection.addStretch();self.count=QLabel(objectName='muted');collection.addWidget(self.count);outer.addLayout(collection)
        self.cards=ReorderableCardList(objectName='cards');self.cards.setItemDelegate(ProjectCardDelegate(self.cards));self.cards.setMouseTracking(True);self.cards.setViewMode(QListView.ViewMode.IconMode);self.cards.setResizeMode(QListView.ResizeMode.Adjust);self.cards.setMovement(QListView.Movement.Static);self.cards.setDragEnabled(True);self.cards.setAcceptDrops(True);self.cards.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove);self.cards.setDefaultDropAction(Qt.DropAction.MoveAction);self.cards.setGridSize(QSize(334,200));self.cards.setSpacing(6);self.cards.itemActivated.connect(lambda i:self.openProject.emit(i.data(Qt.ItemDataRole.UserRole)));self.cards.orderChanged.connect(self.persist_order);outer.addWidget(self.cards,1);self.reload()
    def reload(self):
        self.cards.clear()
        for p in self.db.get_all_projects():
            p=dict(p);p['node_count']=len(self.db.get_all_nodes_for_project(p['id']))
            item=QListWidgetItem(p['title']);item.setToolTip('Double-click or press Enter to open');item.setData(Qt.ItemDataRole.UserRole,p);item.setSizeHint(QSize(326,192));self.cards.addItem(item)
        self.count.setText(f'{self.cards.count()} PROJECT'+('' if self.cards.count()==1 else 'S')+'   ·   DRAG TO REORDER')
    def filter(self,value):
        value=value.lower()
        for i in range(self.cards.count()):
            item=self.cards.item(i);p=item.data(Qt.ItemDataRole.UserRole);item.setHidden(value not in (p['title']+' '+(p.get('description') or '')).lower())
    def selected(self):return self.cards.currentItem().data(Qt.ItemDataRole.UserRole) if self.cards.currentItem() else None
    def new_project(self):
        title,ok=QInputDialog.getText(self,'New project','Project name')
        if ok and title.strip():
            desc,_=QInputDialog.getText(self,'Project description','Short description (optional)');self.db.create_project(title.strip(),desc.strip(),self.cards.count());self.reload()
    def delete_selected(self):
        p=self.selected()
        if p and QMessageBox.question(self,'Delete project',f"Delete '{p['title']}' and all its contents?")==QMessageBox.StandardButton.Yes:self.db.delete_project(p['id']);self.reload()
    def persist_order(self):
        for i in range(self.cards.count()):
            p=self.cards.item(i).data(Qt.ItemDataRole.UserRole);self.db.update_project(p['id'],p['title'],p.get('description') or '',i)
    def import_project(self):
        path,_=QFileDialog.getOpenFileName(self,'Import project','','Tarizz project (*.tarizz)')
        if path:
            try:
                from project_archive import import_project_package
                import_project_package(path,self.db);self.reload()
            except Exception as e:QMessageBox.critical(self,'Import failed',str(e))
    def export_menu(self):
        p=self.selected()
        if not p:QMessageBox.information(self,'Select project','Select a project card first.');return
        menu=QMenu(self);menu.addAction('Tarizz package',lambda:self.export_package(p));menu.addAction('Plain text',lambda:self.export_text(p));menu.addAction('PDF',lambda:self.export_pdf(p));menu.exec(self.cursor().pos())
    def export_package(self,p):
        path,_=QFileDialog.getSaveFileName(self,'Export project',p['title']+'.tarizz','Tarizz project (*.tarizz)')
        if path:
            from project_archive import export_project_package
            export_project_package(p['id'],path,self.db)
    def export_text(self,p):
        path,_=QFileDialog.getSaveFileName(self,'Export text',p['title']+'.txt','Text (*.txt)')
        if not path:return
        nodes=self.db.get_all_nodes_for_project(p['id']);children={}
        for n in nodes:children.setdefault(n['parent_id'],[]).append(n)
        lines=[p['title'],'='*len(p['title']),'']
        def walk(parent,depth=0):
            for n in children.get(parent,[]):
                lines.append('  '*depth+n['name'])
                if n['node_type']=='subpage':
                    d=self.db.load_subpage(n['id']) or {};body=d if isinstance(d,str) else d.get('content','');lines.extend('  '*(depth+1)+x for x in body.splitlines())
                walk(n['id'],depth+1)
        walk(None)
        with open(path,'w',encoding='utf-8') as f:f.write('\n'.join(lines))
    def export_pdf(self,p):
        path,_=QFileDialog.getSaveFileName(self,'Export PDF',p['title']+'.pdf','PDF (*.pdf)')
        if path:
            try:
                import backend.database as database
                from project_export import ProjectExporter
                ProjectExporter(p['id'],p['title'],database).export_to_pdf(path)
                QMessageBox.information(self,'Export complete',f'PDF saved to:\n{path}')
            except Exception as exc:QMessageBox.critical(self,'Export failed',str(exc))


class ProjectPage(QWidget):
    def __init__(self,db,project):
        super().__init__();self.setObjectName('page');self.db=db;self.project=project;self.editors={}
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0)
        sub=QFrame(objectName='projectHeader');bar=QHBoxLayout(sub);bar.setContentsMargins(24,13,20,13);head=QVBoxLayout();head.setSpacing(1);head.addWidget(QLabel('PROJECT WORKSPACE',objectName='eyebrow'));head.addWidget(QLabel(project['title'],objectName='title'));bar.addLayout(head);bar.addStretch();bar.addWidget(btn('＋  New',self.node_menu,'primary','Add note, folder or flowchart'));bar.addWidget(btn('•••',self.more_menu,'icon','Project actions'));layout.addWidget(sub)
        split=QSplitter();left=QFrame(objectName='projectSidebar');left.setMaximumWidth(360);left.setMinimumWidth(230);l=QVBoxLayout(left);l.setContentsMargins(15,19,12,14);explorer=QHBoxLayout();explorer.addWidget(QLabel('EXPLORER',objectName='eyebrow'));explorer.addStretch();explorer.addWidget(QLabel('ONE-CLICK OPEN',objectName='eyebrow'));l.addLayout(explorer);self.search=QLineEdit(placeholderText='⌕  Filter pages');self.search.setClearButtonEnabled(True);self.search.textChanged.connect(self.filter);l.addWidget(self.search);self.tree=QTreeWidget();self.tree.setHeaderHidden(True);self.tree.itemClicked.connect(self.open_item);self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu);self.tree.customContextMenuRequested.connect(self.context);l.addWidget(self.tree,1);side_footer=QLabel('Right-click for rename and delete',objectName='muted');l.addWidget(side_footer);split.addWidget(left)
        self.tabs=QTabWidget();self.tabs.setTabsClosable(True);self.tabs.tabCloseRequested.connect(self.close_tab);split.addWidget(self.tabs);split.setStretchFactor(1,1);layout.addWidget(split,1);self.reload_tree();self.show_welcome()
    def show_welcome(self):
        page=QWidget(objectName='page');v=QVBoxLayout(page);v.setContentsMargins(40,40,40,40);v.addStretch();icon=QLabel('✦',objectName='welcomeIcon');icon.setAlignment(Qt.AlignmentFlag.AlignCenter);icon.setFixedSize(62,62);v.addWidget(icon,0,Qt.AlignmentFlag.AlignHCenter);v.addSpacing(16);title=QLabel('Build something worth keeping',objectName='emptyTitle');title.setAlignment(Qt.AlignmentFlag.AlignCenter);v.addWidget(title);x=QLabel('Open a page from the explorer, or begin with a new note.\nEverything stays inside this project workspace.',objectName='muted');x.setAlignment(Qt.AlignmentFlag.AlignCenter);v.addWidget(x);v.addSpacing(15);v.addWidget(btn('＋  Create a note',lambda:self.add('subpage'),'primary'),0,Qt.AlignmentFlag.AlignHCenter);v.addStretch();self.tabs.addTab(page,'Start')
    def reload_tree(self):
        self.tree.clear();root=QTreeWidgetItem([self.project['title']]);root.setData(0,Qt.ItemDataRole.UserRole,{'root':True});self.tree.addTopLevelItem(root);mapping={None:root};pending=self.db.get_all_nodes_for_project(self.project['id'])
        while pending:
            moved=False
            for n in pending[:]:
                if n['parent_id'] in mapping:
                    icon={'folder':'','subpage':'▤  ','flowchart':'◇  '}[n['node_type']];item=QTreeWidgetItem([f"{icon}{n['name']}"]);item.setToolTip(0,{'folder':'Folder','subpage':'Note','flowchart':'Flowchart'}[n['node_type']]);item.setData(0,Qt.ItemDataRole.UserRole,n);mapping[n['id']]=item;mapping[n['parent_id']].addChild(item);pending.remove(n);moved=True
            if not moved:break
        root.setExpanded(True)
    def parent_id(self):
        item=self.tree.currentItem();n=item.data(0,Qt.ItemDataRole.UserRole) if item else None
        return n['id'] if n and not n.get('root') and n['node_type']=='folder' else None
    def node_menu(self):
        m=QMenu(self);m.addAction('New note',lambda:self.add('subpage'));m.addAction('New folder',lambda:self.add('folder'));m.addAction('New flowchart',lambda:self.add('flowchart'));m.exec(self.cursor().pos())
    def add(self,kind):
        name,ok=QInputDialog.getText(self,'Create item','Name')
        if ok and name.strip():self.db.create_node(self.project['id'],self.parent_id(),kind,name.strip());self.reload_tree()
    def open_item(self,item,col=0):
        n=item.data(0,Qt.ItemDataRole.UserRole)
        if not n:return
        if n.get('root') or n['node_type']=='folder':item.setExpanded(not item.isExpanded());return
        if n['id'] in self.editors:self.tabs.setCurrentWidget(self.editors[n['id']]);return
        page=FlowchartPage(self.db,n) if n['node_type']=='flowchart' else RichEditor(self.db,n,self);self.editors[n['id']]=page;self.tabs.setCurrentIndex(self.tabs.addTab(page,n['name']))
    def close_tab(self,index):
        w=self.tabs.widget(index)
        if hasattr(w,'save'):w.save()
        for k,v in list(self.editors.items()):
            if v is w:del self.editors[k]
        self.tabs.removeTab(index)
    def context(self,pos):
        item=self.tree.itemAt(pos);m=QMenu(self);m.addAction('New note',lambda:self.add('subpage'));m.addAction('New folder',lambda:self.add('folder'));m.addAction('New flowchart',lambda:self.add('flowchart'))
        if item:
            n=item.data(0,Qt.ItemDataRole.UserRole)
            if n and not n.get('root'):m.addSeparator();m.addAction('Rename',lambda:self.rename(item,n));m.addAction('Delete',lambda:self.delete(item,n))
        m.exec(self.tree.viewport().mapToGlobal(pos))
    def rename(self,item,n):
        name,ok=QInputDialog.getText(self,'Rename','Name',text=n['name'])
        if ok and name.strip():self.db.rename_node(n['id'],name.strip());self.reload_tree()
    def delete(self,item,n):
        if QMessageBox.question(self,'Delete',f"Delete '{n['name']}'?")==QMessageBox.StandardButton.Yes:self.db.delete_node(n['id']);self.reload_tree()
    def filter(self,text):
        term=text.lower()
        def visit(item):
            yes=term in item.text(0).lower()
            for i in range(item.childCount()):yes=visit(item.child(i)) or yes
            item.setHidden(not yes);return yes
        for i in range(self.tree.topLevelItemCount()):visit(self.tree.topLevelItem(i))
    def more_menu(self):self.node_menu()
    def save(self):
        for w in self.editors.values():
            if hasattr(w,'save'):w.save()


class TarizzWindow(QMainWindow):
    def __init__(self,auth):
        super().__init__();self.auth=auth;self.db=get_db();self.dark=False;self.history=[];self.future=[]
        self.setWindowTitle('Tarizz');self.resize(1380,850);self.setMinimumSize(1020,650)
        root=QWidget(objectName='page');self.setCentralWidget(root);v=QVBoxLayout(root);v.setContentsMargins(0,0,0,0);v.setSpacing(0)
        top=QFrame(objectName='topbar');h=QHBoxLayout(top);h.setContentsMargins(20,10,20,10);h.setSpacing(6);self.back_btn=btn('←',self.back,'icon','Back');self.forward_btn=btn('→',self.forward,'icon','Forward');h.addWidget(self.back_btn);h.addWidget(self.forward_btn);h.addSpacing(9);h.addWidget(QLabel('TARIZZ',objectName='brand'));h.addSpacing(12);self.location=QLabel('Projects',objectName='muted');h.addWidget(self.location);h.addStretch();nav=QFrame(objectName='navPill');nav_row=QHBoxLayout(nav);nav_row.setContentsMargins(3,3,3,3);nav_row.setSpacing(1);self.projects_nav=btn('Projects',lambda:self.navigate(self.dashboard,'Projects'),'navButton');self.calendar_nav=btn('Calendar',self.calendar,'navButton');self.diary_nav=btn('Diary',self.diary,'navButton');self.nav_buttons=[self.projects_nav,self.calendar_nav,self.diary_nav]
        for item in self.nav_buttons:nav_row.addWidget(item)
        h.addWidget(nav);h.addSpacing(7);self.theme=btn('◐',self.toggle_theme,'icon','Toggle light/dark mode');h.addWidget(self.theme);v.addWidget(top)
        self.stack=QStackedWidget();v.addWidget(self.stack,1);self.dashboard=DashboardPage(self.db);self.dashboard.openProject.connect(self.project);self.dashboard.openCalendar.connect(self.calendar);self.dashboard.openDiary.connect(self.diary);self.stack.addWidget(self.dashboard);self.apply_theme();self.update_nav()
        for shortcut,slot in (('Alt+1',lambda:self.navigate(self.dashboard,'Projects')),('Alt+2',self.calendar),('Alt+3',self.diary),('Ctrl+Shift+F',self.focus_search),('Ctrl+N',self.new_project_shortcut)):
            action=QAction(self);action.setShortcut(QKeySequence(shortcut));action.triggered.connect(slot);self.addAction(action)
    def navigate(self,page,label,push=True):
        current=self.stack.currentWidget()
        if hasattr(self,'diary_page') and current is self.diary_page and page is not current:
            self.diary_page.lock()
        if push and current is not page:self.history.append((current,self.location.text()));self.future.clear()
        if self.stack.indexOf(page)<0:self.stack.addWidget(page)
        self.stack.setCurrentWidget(page);self.location.setText(label);self.update_nav();self.update_active_navigation(page)
    def back(self):
        if self.history:self.future.append((self.stack.currentWidget(),self.location.text()));page,label=self.history.pop();self.navigate(page,label,False)
    def forward(self):
        if self.future:self.history.append((self.stack.currentWidget(),self.location.text()));page,label=self.future.pop();self.navigate(page,label,False)
    def update_nav(self):self.back_btn.setEnabled(bool(self.history));self.forward_btn.setEnabled(bool(self.future))
    def update_active_navigation(self,page=None):
        page=page or self.stack.currentWidget();active=self.projects_nav if page is self.dashboard or isinstance(page,ProjectPage) else self.calendar_nav if hasattr(self,'planner') and page is self.planner else self.diary_nav if hasattr(self,'diary_page') and page is self.diary_page else None
        for item in self.nav_buttons:
            item.setProperty('active','true' if item is active else 'false');item.style().unpolish(item);item.style().polish(item)
    def focus_search(self):
        self.navigate(self.dashboard,'Projects');self.dashboard.search.setFocus();self.dashboard.search.selectAll()
    def new_project_shortcut(self):
        self.navigate(self.dashboard,'Projects');self.dashboard.new_project()
    def project(self,p):self.navigate(ProjectPage(self.db,p),p['title'])
    def calendar(self):
        if not hasattr(self,'planner'):self.planner=PlannerPage(self.db)
        self.planner.reload_projects();self.navigate(self.planner,'Calendar & tasks')
    def diary(self):
        if not hasattr(self,'diary_page'):self.diary_page=DiaryPage(self.db,self)
        self.navigate(self.diary_page,'Private diary');self.diary_page.unlock()
    def toggle_theme(self):self.dark=not self.dark;self.apply_theme()
    def apply_theme(self):
        c=DARK if self.dark else LIGHT;css=stylesheet(c);app=QApplication.instance();app.setStyleSheet(css);self.setStyleSheet(css)
        palette=QPalette();palette.setColor(QPalette.ColorRole.Window,QColor(c['bg']));palette.setColor(QPalette.ColorRole.WindowText,QColor(c['text']));palette.setColor(QPalette.ColorRole.Base,QColor(c['surface']));palette.setColor(QPalette.ColorRole.AlternateBase,QColor(c['soft']));palette.setColor(QPalette.ColorRole.Text,QColor(c['text']));palette.setColor(QPalette.ColorRole.Button,QColor(c['surface']));palette.setColor(QPalette.ColorRole.ButtonText,QColor(c['text']));palette.setColor(QPalette.ColorRole.Highlight,QColor(c['accent']));palette.setColor(QPalette.ColorRole.HighlightedText,QColor('#ffffff'));palette.setColor(QPalette.ColorRole.Link,QColor(c['accent']));palette.setColor(QPalette.ColorRole.ToolTipBase,QColor(c['surface']));palette.setColor(QPalette.ColorRole.ToolTipText,QColor(c['text']));app.setPalette(palette)
        self.theme.setText('☀' if self.dark else '◐');self.theme.setToolTip('Use light mode' if self.dark else 'Use dark mode');self.dashboard.cards.viewport().update();self.update_active_navigation()
    def closeEvent(self,event):
        for i in range(self.stack.count()):
            w=self.stack.widget(i)
            if hasattr(w,'save'):w.save()
        event.accept()


def run_qt_app(auth_manager):
    app=QApplication.instance() or QApplication([]);app.setApplicationName('Tarizz');app.setStyle('Fusion');window=TarizzWindow(auth_manager);window.show();return app.exec()
