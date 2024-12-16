import os
from glob import glob
from PySide2.QtCore import QObject, Signal, Qt, QCoreApplication, QEvent, QTimer
from axipy import (CurrentSettings, data_manager, CoordSystem, ChooseCoordSystemDialog,
                   provider_manager, Feature, Notifications, Schema)
from PySide2.QtWidgets import QDialog, QTableWidgetItem, QFileDialog, QDialogButtonBox
from PySide2.QtUiTools import QUiLoader
from PySide2.QtGui import QIcon
from typing import Union
from PySide2 import QtCore

class MyDialog(QDialog):
    def __init__(self, parent):
        super(MyDialog, self).__init__(parent)
        ui_file = os.path.join(os.path.dirname(__file__), "exports_tabs.ui")
        self.ui = QUiLoader().load(ui_file, parent)

        icon_path = os.path.join(os.path.dirname(__file__), "icon/logo.png")  # Путь к иконке
        self.ui.setWindowIcon(QIcon(icon_path))
      
      # Настройка Progress Bar
        self.ui.progBar_tab.setValue(0)
        self.ui.progBar_data.setValue(0)

        self.ui.lineEdit_way.setReadOnly(True)
        self.ui.lineEdit_CK.setReadOnly(True)
        self.ui.toolB_selectWay.clicked.connect(self.set_filepath)
        self.ui.toolB_selectCK.clicked.connect(self.set_coords)

      # Флаг состояния завершения задачи
        self.is_task_completed = False

      # Флаг выполнения задачи
        self.is_task_running = False

      # Флаг отмены
        self.is_canceled = False

   # Выполнение нажатия кнопок
       # Кнопка "Ок"
        self.ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)

        self.ui.buttonBox.button(QDialogButtonBox.Ok).clicked.disconnect()
        self.ui.buttonBox.button(QDialogButtonBox.Ok).clicked.connect(self.on_ok_clicked)

       # Кнопка "Отмена"
        self.ui.buttonBox.button(QDialogButtonBox.Cancel).clicked.disconnect()
        self.ui.buttonBox.button(QDialogButtonBox.Cancel).setText("Закрыть")
        self.ui.buttonBox.button(QDialogButtonBox.Cancel).clicked.connect(self.on_cancel_clicked)

       # Для кнопки "Х" устанавливаем фильтр событий на диалог
        self.ui.installEventFilter(self)

       # Check box "Выбрать все"
        self.ui.checkBox_selectAll.stateChanged.connect(self.select_all_tables)

       # Отслеживание изменений в таблице
        self.ui.tableWidget.itemChanged.connect(self.update_ok_button_state)

   # Отображение всех открытых таблиц
    def set_tab_name(self):
        tables = data_manager.tables
        self.ui.tableWidget.setColumnCount(1)
        self.ui.tableWidget.setRowCount(len(tables))
        self.ui.tableWidget.verticalHeader().setVisible(False)

        name_t = []
        for t in tables:
            name_t.append(t.name)
        self.ui.tableWidget.setHorizontalHeaderLabels(['Таблицы'])

       # Настройка Check box, для выбора таблиц
        for row, string in enumerate(name_t, 0):
            chkBoxItem = QTableWidgetItem(string)
            chkBoxItem.setText(string)
            chkBoxItem.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chkBoxItem.setCheckState(Qt.Unchecked)
            self.ui.tableWidget.setItem(row, 0, chkBoxItem)

  # Проверка состояния чекбоксов и обновление состояния кнопки "ОК"
    def update_ok_button_state(self):
        any_checked = False
        all_checked = True

        for row in range(self.ui.tableWidget.rowCount()):
            item = self.ui.tableWidget.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                any_checked = True
            else:
                all_checked = False

        self.ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(any_checked)

      # Обновляем состояние чекбокса "Выбрать все"
        self.ui.checkBox_selectAll.blockSignals(True)
        self.ui.checkBox_selectAll.setCheckState(Qt.Checked if all_checked else Qt.Unchecked)
        self.ui.checkBox_selectAll.blockSignals(False)

# Функционал работы Check box "Выбрать все"
  # Выставление значений при нажатии на check box "Выбрать все"
    def select_all_tables(self, state):
      # Проходим по всем элементам таблицы и устанавливаем состояние чекбоксов
        for row in range(self.ui.tableWidget.rowCount()):
            item = self.ui.tableWidget.item(row, 0)
            item.setCheckState(Qt.Checked if state == Qt.Checked else Qt.Unchecked)

  # Отображение пути при открытии
    def first_filepath(self):
        self.last_save_path = CurrentSettings.LastSavePath
        if not self.last_save_path.exists():
            first_filepath = str(CurrentSettings.LastOpenPath)
        else:
            first_filepath = str(self.last_save_path)

        self.ui.lineEdit_way.setText(first_filepath)

  # Отображение выбранного пути
    def set_filepath(self):
        self.assign_a_path = QFileDialog.getExistingDirectory()
        self.ui.lineEdit_way.setText(self.assign_a_path)

  # Отображение системы координат
    def first_coords(self):
        tables = data_manager.tables
        self.result_cs = tables[0].schema.coordsystem
        self.ui.lineEdit_CK.setText(self.result_cs.title)

  # Отображение выбранной системы координат
    def set_coords(self):
        csMercator = CoordSystem.from_prj('10, 104, 7, 0')
        dialog = ChooseCoordSystemDialog(csMercator)
        if dialog.exec() == QDialog.Accepted:
            self.result_cs = dialog.chosenCoordSystem()
            self.ui.lineEdit_CK.setText(self.result_cs.title)

  # Прогресс бар для таблицы
    def setProgress_tab(self, progress, text):
        self.ui.progBar_tab.setFormat(text + "    %p%")
        self.ui.progBar_tab.setValue(progress)

  # Прогресс бар для элементов таблицы
    def setProgress_data(self, progress):
        self.ui.progBar_data.setValue(progress)

  # Функционал кнопки "Ок"
    def on_ok_clicked(self):
            self.run_button()

  # Функционал кнопки "Отмена" и кнопки "X"
    @QtCore.Slot()
    def on_cancel_clicked(self):
        if self.is_task_running and self.task:
            self.task.cancel()  # Устанавливаем флаг отмены
            self.is_canceled = True
            self.ui.removeEventFilter(self)
        else:
          # Если задача не запущена, закрываем диалог
            self.ui.progBar_tab.setValue(0)
            self.ui.progBar_data.setValue(0)
            self.ui.progBar_tab.setFormat("" + "    %p%")
            self.ui.removeEventFilter(self)
            self.ui.close()

   # Функционал кнопки "X"
    def eventFilter(self, watched, event):
        if watched is self.ui and event.type() == QEvent.Close:
            self.on_cancel_clicked()
            return True
        return super(MyDialog, self).eventFilter(watched, event)

    def finalize_task(self):
        self.ui.progBar_tab.setValue(0)
        self.ui.progBar_data.setValue(0)
        self.ui.progBar_tab.setFormat("" + "    %p%")

      # Сбрасываем состояния чекбоксов
        for row in range(self.ui.tableWidget.rowCount()):
            item = self.ui.tableWidget.item(row, 0)
            if item is not None:
                item.setCheckState(Qt.Unchecked)

        self.is_task_running = False
        self.is_task_completed = True
        self.ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)  # Включаем кнопку после завершения задачи
        self.ui.buttonBox.button(QDialogButtonBox.Cancel).setText("Закрыть")

  # Запуск экспорта
    def run_button(self):
        self.ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
        self.ui.buttonBox.button(QDialogButtonBox.Cancel).setText("Отмена")

      # Функционал взятия имен таблиц
        try:
            checked_items = []
            for row in range(self.ui.tableWidget.rowCount()):
                item = self.ui.tableWidget.item(row, 0)
                if item.checkState() == Qt.Checked:
                    checked_items.append(item.text())

          # Определение конечного пути
            filepath = self.ui.lineEdit_way.text()

          # Определение системы координат
            coord = self.result_cs

            self.is_task_running = True
          
          # Запуск самой задачи
            self.task = CopyTablesInFile(list_name=checked_items, filepath=filepath, coords=coord)
            self.task.upProg_exp_tab.connect(self.setProgress_tab)
            self.task.upProg_exp_feat.connect(self.setProgress_data)
            self.task.run()

        finally:
            self.is_task_running = False
          # Проверяем флаг отмены
            if self.is_canceled:
                self.ui.progBar_tab.setValue(0)
                self.ui.progBar_data.setValue(0)
                self.ui.progBar_tab.setFormat("" + "    %p%")
                self.is_canceled = False  # Сбрасываем флаг отмены

              # Устанавливаем флаги завершения задачи и активируем кнопку "ОК"
                self.is_task_running = False
                self.is_task_completed = True
                self.ui.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)  # Включаем кнопку после завершения задачи
                self.ui.buttonBox.button(QDialogButtonBox.Cancel).setText("Закрыть")
            else:
                QTimer.singleShot(2000, self.finalize_task)  # Задержка 2000 мс (2 секунды)

    def show(self):
        self.set_tab_name()
        self.first_filepath()
        self.first_coords()

        return self.ui.show()


class CopyTablesInFile(QObject):
    upProg_exp_feat = Signal(int)
    upProg_exp_tab = Signal(int, str)

    def __init__(self, list_name, filepath, coords):
        super().__init__()
        self.list_name = list_name  # Названия таблиц
        self.filepath = filepath    # Путь для сохранения
        self.coords = coords        # Система координат

        self.processed_ids = set()
        self.total_items = 0  # Общее количество элементов во всех таблицах
        self.processed_items = 0

        self.is_cancel = False  # Флаг отмены задачи
        self.last_created_file = None  # Сохранение пути последнего файла

        self.completed_tables = 0

        self.title = "Конвертация отменена."
        self.title1 = "Экспорт таблиц"
        ''' CoordSystem текущей исходной таблицы'''
        self.__cs_curent_table=None
        ''' CoordSystem текущей результирующей  таблицы'''
        self.__cs_out_current=None

  # Устанавливаем флаг отмены
    def cancel(self):
        self.is_cancel = True

  # Удаление последнего файла при выполнении "Отмены"
    def del_file(self):
        if self.last_created_file:
            base_name, _ = os.path.splitext(self.last_created_file)
            related_files = glob(f"{base_name}.*")  # Находим все файлы с таким же именем, но разными расширениями

            for file_path in related_files:
                try:
                    os.remove(file_path)
                    Notifications.push(self.title,f"Файл {file_path} успешно удален.",Notifications.Critical)

                except Exception as e:
                    Notifications.push(self.title,f"Ошибка при удалении файла {file_path}: {e}",Notifications.Critical)

          # Уведомление об отмене
            Notifications.push(
                self.title1,
                f"Конвертация завершена.\nСконвертировано файлов: {(self.completed_tables - 1)} из {len(self.list_name)}."
            )

    def run(self):
        total_tables = len(self.list_name)

        for t in data_manager.tables:

            for name in self.list_name:
                if self.is_cancel:
                    self.del_file()
                    return False
                else:
                    if t.name == name:
                        self.total_items = 0
                        self.processed_items = 0
                        self.total_items = t.count()

                        #schema = t.schema
                        #schema.coordsystem = self.coords

                      # Для того, чтобы сохранялись охваты
                        attrs = [t.schema.by_name(name) for name in t.schema.attribute_names]
                        ''' Если исходная coordsystem план-схема определяем bound '''
                        if t.coordsystem.non_earth:
                            bound=t.get_bounds()
                            out_cs=self.coords
                            out_cs.rect=bound
                            schema = Schema(*attrs, coordsystem=out_cs)
                        else:
                            schema = Schema(*attrs, coordsystem=self.coords)
                        self.__cs_curent_table=t.coordsystem
                        self.__cs_out_current=schema.coordsystem
                        filepath = f'{self.filepath}/{t.name}.TAB'
                        self.last_created_file = filepath
                        dest = provider_manager.tab.get_destination(filepath, schema)
                        t.schema.coordsystem.rect = self.coords.rect
                        dest.export(t.items(), func_callback=self.func_exp_feat)

                        self.completed_tables += 1
                        overall_progress = int((self.completed_tables / total_tables) * 100)
                        self.upProg_exp_tab.emit(overall_progress, f"{t.name}")

                        QCoreApplication.processEvents()
                        break
                    else:
                        continue

        Notifications.push(
            self.title1,
            f"Конвертация завершена.\n " + f"Сконвертировано файлов: " + f"{self.completed_tables} из {len(self.list_name)}.")

  # Фун-ция для прогресс-бара для экспорта фич таблицы
    def func_exp_feat(self, feature: Feature, row: int) -> Union[None, bool]:
        if self.is_cancel:
            return False
        else:
            self.processed_items += 1
            ''' Если исходная  coordsystem план- схема , устанавливаем coordsytem выходной проекции из схемы'''
            if self.__cs_curent_table.non_earth:
                if feature.geometry is not None:
                    feature.geometry.coordsystem=self.__cs_out_current
            overall_progress = int(self.processed_items * 100 / self.total_items)
            self.upProg_exp_feat.emit(overall_progress)
            QCoreApplication.processEvents()
