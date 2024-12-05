from axipy import Plugin, ActionButton, view_manager, ObserverManager
from .export_files import MyDialog
from axipy._internal._menu_file_position import _MenuFilePosition
from PySide2.QtGui import QIcon

class ExamplePluginMinimal(Plugin):
    def __init__(self)-> None:
        self._title = self.tr("Сохранение копий таблиц")

        self.button = ActionButton(
            "Сохранить копии таблиц...",
            on_click=self.open_dialog,
            enable_on= ObserverManager.HasTables,
            icon=QIcon.fromTheme("table_save_copy_as"))

        menu = _MenuFilePosition()
        menu.insert_after(self.button, "CloseTable") # Закрыть таблицы...

    def unload(self)-> None:
        self.button.remove()

    def open_dialog(self)-> None:
        dialog = MyDialog(view_manager.global_parent)
        dialog.resize(500, 300)
        dialog.show()
