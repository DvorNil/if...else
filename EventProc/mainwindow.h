#pragma once

#include <QMainWindow>
#include <QTableWidget>
#include <QPushButton>
#include <QLineEdit>
#include <QComboBox>
#include <QTextEdit>
#include <QDateTimeEdit>
#include <QDoubleSpinBox>
#include <QTabWidget>
#include "Event.h"
#include "QEventDatabase.h"
#include "FilterDialog.h"


class MainWindow : public QMainWindow {
    Q_OBJECT

public:
    explicit MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

private slots:
    void onAddEventClicked();
    void onFilterEventsClicked();


private:
    // Основные виджеты
    QTableWidget *eventsTable;

    // Виджеты ввода данных
    QLineEdit *titleEdit;
    QTextEdit *descriptionEdit;
    QLineEdit *organizerEdit;
    QComboBox *formatCombo;
    QDateTimeEdit *startTimeEdit;
    QDateTimeEdit *durationEdit;

    // Виджеты локации
    QLineEdit *addressEdit;
    QLineEdit *cityEdit;
    QLineEdit *countryEdit;
    QDoubleSpinBox *latEdit;
    QDoubleSpinBox *lonEdit;

    // Контактная информация
    QLineEdit *emailEdit;
    QLineEdit *phoneEdit;
    QLineEdit *websiteEdit;

    // Медиа-контент
    QLineEdit *primaryImageEdit;
    QLineEdit *galleryUrlsEdit;
    QLineEdit *videoUrlEdit;

    QLineEdit *tagsEdit;
    QPushButton *addButton;
    QPushButton *filterButton;

    // Вспомогательные методы
    QString joinStrings(const std::vector<std::string>&, const std::string&);
    void setupUI();
    void refreshEventsTable(const std::vector<Event>& events);
    std::vector<std::string> splitString(const QString& input);
    std::tm QDateTimeToTm(const QDateTime& qdt);
    QString formatTime(const std::tm& tm);

    // Вкладки
    QTabWidget *tabs;
    QWidget *mainTab;
    QWidget *locationTab;
    QWidget *contactsTab;
    QWidget *mediaTab;

    std::vector<std::string> splitString(const QString& input) const;
    //QEventDatabase::SortBy currentSortOrder = QEventDatabase::SortBy::Date;
    void sortEvents(std::vector<Event>& events, QEventDatabase::SortBy sortBy, const GeoCoordinates& userCoords = {0,0});
};
