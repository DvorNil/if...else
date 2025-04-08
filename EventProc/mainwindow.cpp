#include "mainwindow.h"
#include "EventDatabase.h"
#include <QHeaderView>
#include <QFormLayout>
#include <QMessageBox>
#include <QDateTimeEdit>
#include <QDoubleSpinBox>

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
{
    setupUI();
    refreshEventsTable(QEventDatabase::getInstance().getEventsByFilters(Event::Format::Offline));
}

void MainWindow::setupUI() {
    QWidget *centralWidget = new QWidget(this);
    setCentralWidget(centralWidget);

    // Основные виджеты
    eventsTable = new QTableWidget(this);
    titleEdit = new QLineEdit(this);
    descriptionEdit = new QTextEdit(this);
    organizerEdit = new QLineEdit(this);
    formatCombo = new QComboBox(this);
    startTimeEdit = new QDateTimeEdit(QDateTime::currentDateTime(), this);
    durationEdit = new QDateTimeEdit(QDateTime::fromSecsSinceEpoch(0), this);
    durationEdit->setDisplayFormat("HH:mm:ss");

    // Виджеты для локации
    addressEdit = new QLineEdit(this);
    cityEdit = new QLineEdit(this);
    countryEdit = new QLineEdit(this);
    latEdit = new QDoubleSpinBox(this);
    lonEdit = new QDoubleSpinBox(this);
    latEdit->setRange(-90, 90);
    lonEdit->setRange(-180, 180);

    // Контактная информация
    emailEdit = new QLineEdit(this);
    phoneEdit = new QLineEdit(this);
    websiteEdit = new QLineEdit(this);

    // Медиа-контент
    primaryImageEdit = new QLineEdit(this);
    galleryUrlsEdit = new QLineEdit(this);
    videoUrlEdit = new QLineEdit(this);

    tagsEdit = new QLineEdit(this);
    addButton = new QPushButton("Добавить мероприятие", this);
    filterButton = new QPushButton("Фильтровать", this);

    // Настройка таблицы
    eventsTable->setColumnCount(8);
    eventsTable->setHorizontalHeaderLabels({
        "Название",
        "Организатор",
        "Формат",
        "Город",
        "Дата начала",
        "Продолжительность",
        "Теги",
        "Контакты"
    });
    eventsTable->horizontalHeader()->setSectionResizeMode(QHeaderView::Interactive);

    // Компоновка интерфейса
    QTabWidget *tabs = new QTabWidget(this);
    QWidget *mainTab = new QWidget(this);
    QWidget *locationTab = new QWidget(this);
    QWidget *contactsTab = new QWidget(this);
    QWidget *mediaTab = new QWidget(this);

    // Основная вкладка
    QFormLayout *mainForm = new QFormLayout(mainTab);
    mainForm->addRow("Название:", titleEdit);
    mainForm->addRow("Описание:", descriptionEdit);
    mainForm->addRow("Организатор:", organizerEdit);
    mainForm->addRow("Формат:", formatCombo);
    mainForm->addRow("Дата начала:", startTimeEdit);
    mainForm->addRow("Продолжительность:", durationEdit);
    mainForm->addRow("Теги (через запятую):", tagsEdit);

    // Вкладка локации
    QFormLayout *locationForm = new QFormLayout(locationTab);
    locationForm->addRow("Адрес:", addressEdit);
    locationForm->addRow("Город:", cityEdit);
    locationForm->addRow("Страна:", countryEdit);
    locationForm->addRow("Широта:", latEdit);
    locationForm->addRow("Долгота:", lonEdit);

    // Вкладка контактов
    QFormLayout *contactsForm = new QFormLayout(contactsTab);
    contactsForm->addRow("Email:", emailEdit);
    contactsForm->addRow("Телефон:", phoneEdit);
    contactsForm->addRow("Веб-сайт:", websiteEdit);

    // Вкладка медиа
    QFormLayout *mediaForm = new QFormLayout(mediaTab);
    mediaForm->addRow("Основное изображение:", primaryImageEdit);
    mediaForm->addRow("Галерея (URL через запятую):", galleryUrlsEdit);
    mediaForm->addRow("Видео URL:", videoUrlEdit);

    tabs->addTab(mainTab, "Основное");
    tabs->addTab(locationTab, "Локация");
    tabs->addTab(contactsTab, "Контакты");
    tabs->addTab(mediaTab, "Медиа");

    // Основной лейаут
    QVBoxLayout *mainLayout = new QVBoxLayout(centralWidget);
    mainLayout->addWidget(tabs);
    mainLayout->addWidget(addButton);
    mainLayout->addWidget(filterButton);
    mainLayout->addWidget(eventsTable);

    formatCombo->addItems({"Online", "Offline"});

    connect(addButton, &QPushButton::clicked, this, &MainWindow::onAddEventClicked);
    connect(filterButton, &QPushButton::clicked, this, &MainWindow::onFilterEventsClicked);
}

void MainWindow::onAddEventClicked() {
    // Сбор данных локации
    Location location{
        .address = addressEdit->text().toStdString(),
        .city = cityEdit->text().toStdString(),
        .country = countryEdit->text().toStdString(),
        .coordinates = {
            latEdit->value(),
            lonEdit->value()
        }
    };

    // Сбор контактной информации
    ContactInfo contacts{
        .email = emailEdit->text().toStdString(),
        .phone = phoneEdit->text().toStdString(),
        .website = websiteEdit->text().toStdString()
    };

    // Сбор медиа-контента
    MediaContent media{
        .primaryImageUrl = primaryImageEdit->text().toStdString(),
        .galleryUrls = splitString(galleryUrlsEdit->text()),
        .videoUrl = videoUrlEdit->text().toStdString()
    };

    // Преобразование времени
    QDateTime startQdt = startTimeEdit->dateTime();
    QDateTime durationQdt = durationEdit->dateTime();

    std::tm startTime = QDateTimeToTm(startQdt);
    std::tm duration = QDateTimeToTm(durationQdt);

    // Создание события
    Event event(
        titleEdit->text().toStdString(),
        descriptionEdit->toPlainText().toStdString(),
        organizerEdit->text().toStdString(),
        formatCombo->currentText() == "Online" ? Event::Format::Online : Event::Format::Offline,
        startTime,
        duration,
        location,
        splitString(tagsEdit->text()),
        contacts,
        media
        );

    if(QEventDatabase::getInstance().addEvent(event)) {
        refreshEventsTable(QEventDatabase::getInstance().getEventsByFilters(Event::Format::Offline));
        QMessageBox::information(this, "Успех", "Мероприятие добавлено!");
    } else {
        QMessageBox::critical(this, "Ошибка", "Не удалось добавить мероприятие");
    }
}

QString MainWindow::joinStrings(const std::vector<std::string>& strings, const std::string& delimiter) {
    QStringList list;
    for (const auto& s : strings) {
        list << QString::fromStdString(s);
    }
    return list.join(QString::fromStdString(delimiter));
}

void MainWindow::refreshEventsTable(const std::vector<Event>& events) {
    eventsTable->setRowCount(0);

    for(const Event& event : events) {
        int row = eventsTable->rowCount();
        eventsTable->insertRow(row);

        // Преобразование данных в QString
        auto toQString = [](const std::string& s) { return QString::fromStdString(s); };

        // Название и организатор
        eventsTable->setItem(row, 0, new QTableWidgetItem(toQString(event.getTitle())));
        eventsTable->setItem(row, 1, new QTableWidgetItem(toQString(event.getOrganizer())));

        // Формат
        eventsTable->setItem(row, 2, new QTableWidgetItem(
                                         event.getFormat() == Event::Format::Online ? "Online" : "Offline"));

        // Город
        eventsTable->setItem(row, 3, new QTableWidgetItem(toQString(event.getLocation().city)));

        // Время начала и продолжительность
        eventsTable->setItem(row, 4, new QTableWidgetItem(formatTime(event.getStartTime())));
        eventsTable->setItem(row, 5, new QTableWidgetItem(formatTime(event.getDuration())));

        // Теги (объединение через запятую)
        QString tags = joinStrings(event.getTags(), ", ");
        eventsTable->setItem(row, 6, new QTableWidgetItem(tags));

        // Контакты (предполагаем, что toString() возвращает std::string)
        eventsTable->setItem(row, 7, new QTableWidgetItem(
                                         toQString(event.getContacts().toString())));
    }
}

// Вспомогательные функции
std::vector<std::string> MainWindow::splitString(const QString& input) {
    std::vector<std::string> result;
    for(const QString& s : input.split(',')) {
        result.push_back(s.trimmed().toStdString());
    }
    return result;
}

#if defined(_WIN32)
std::tm MainWindow::QDateTimeToTm(const QDateTime& qdt) {
    std::time_t t = qdt.toSecsSinceEpoch();
    std::tm tm;
    localtime_s(&tm, &t); // Для Windows
    return tm;
}
#else
std::tm MainWindow::QDateTimeToTm(const QDateTime& qdt) {
    std::time_t t = qdt.toSecsSinceEpoch();
    std::tm tm;
    localtime_r(&t, &tm); // Для Unix-систем
    return tm;
}
#endif

QString MainWindow::formatTime(const std::tm& tm) {
    return QDateTime::fromSecsSinceEpoch(mktime(const_cast<std::tm*>(&tm))).toString("dd.MM.yyyy HH:mm");
}

void MainWindow::sortEvents(std::vector<Event>& events,
                            QEventDatabase::SortBy sortBy,
                            const GeoCoordinates& userCoords) {
    std::sort(events.begin(), events.end(), [&](const Event& a, const Event& b) {
        switch(sortBy) {
        case QEventDatabase::SortBy::Date: {
            std::tm aTime = a.getStartTime();
            std::tm bTime = b.getStartTime();
            return std::mktime(&aTime) < std::mktime(&bTime);
        }
        case QEventDatabase::SortBy::Distance: {
            return QEventDatabase::calculateDistance(a.getLocation().coordinates, userCoords) <
                   QEventDatabase::calculateDistance(b.getLocation().coordinates, userCoords);
        }
        case QEventDatabase::SortBy::Title:
            return a.getTitle() < b.getTitle();
        }
        return false;
    });
}

void MainWindow::onFilterEventsClicked() {
    FilterDialog dialog(this);
    if(dialog.exec() != QDialog::Accepted) return;

    // Парсим параметры фильтрации
    Event::Format format = Event::Format::Online;
    if(dialog.formatCombo->currentText() == "Online")
        format = Event::Format::Online;
    else if(dialog.formatCombo->currentText() == "Offline")
        format = Event::Format::Offline;

    const std::string city = dialog.cityEdit->text().trimmed().toStdString();

   // GeoCoordinates coords{
   //     dialog.latSpin->value(),
   //     dialog.lonSpin->value()
  //  };
   // const double radiusKm = dialog.radiusSpin->value();

    const std::vector<std::string> tags = splitString(dialog.tagsEdit->text());

    // Получаем отфильтрованные события
    std::vector<Event> filteredEvents = QEventDatabase::getInstance().getEventsByFilters(
        format,
        city,
        {0, 0}, //coords
        -1, // radius
        tags
        );

    // Обновляем таблицу
    refreshEventsTable(filteredEvents);
}

std::vector<std::string> MainWindow::splitString(const QString& input) const {
    std::vector<std::string> result;
    for(const QString& s : input.split(',', Qt::SkipEmptyParts)) {
        result.push_back(s.trimmed().toStdString());
    }
    return result;
}
MainWindow::~MainWindow() {}
