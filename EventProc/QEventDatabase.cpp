#include "QEventDatabase.h"
#include <QSqlError>
#include <QMutexLocker>
#include <QDebug>
#include <QDateTime>

QEventDatabase& QEventDatabase::getInstance() {
    static QEventDatabase instance;
    return instance;
}


QEventDatabase::QEventDatabase() {
    db = QSqlDatabase::addDatabase("QSQLITE", "events_connection");
    db.setDatabaseName("events.db");

    if (!db.open()) {
        qCritical() << "Database error:" << db.lastError().text();
        return;
    }

    initDatabase();
}

QString joinStrings(const std::vector<std::string>& strings, const QString& delimiter) {
    QStringList list;
    for (const auto& s : strings) {
        list << QString::fromStdString(s);
    }
    return list.join(delimiter);
}

bool QEventDatabase::initDatabase() {
    QMutexLocker locker(&dbMutex);

    QSqlQuery query(db);
    QString createTableQuery =
        "CREATE TABLE IF NOT EXISTS events ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "title TEXT NOT NULL UNIQUE,"
        "description TEXT NOT NULL,"
        "organizer TEXT NOT NULL,"
        "format TEXT CHECK(format IN ('Online', 'Offline')),"
        "start_time TEXT NOT NULL,"
        "duration TEXT NOT NULL,"
        "address TEXT,"
        "city TEXT,"
        "country TEXT,"
        "latitude REAL,"
        "longitude REAL,"
        "tags TEXT,"
        "contact_email TEXT,"
        "contact_phone TEXT,"
        "contact_website TEXT,"
        "primary_image_url TEXT,"
        "gallery_urls TEXT,"
        "video_url TEXT)";

    if (!query.exec(createTableQuery)) {
        qCritical() << "Failed to create table:" << query.lastError().text();
        return false;
    }
    return true;
}

bool QEventDatabase::addEvent(const Event& event) {
    QMutexLocker locker(&dbMutex);
    QSqlQuery query(db);

    query.prepare(
        "INSERT INTO events ("
        "title, description, organizer, format, start_time, duration, "
        "address, city, country, latitude, longitude, tags, contact_email, "
        "contact_phone, contact_website, primary_image_url, gallery_urls, video_url"
        ") VALUES ("
        ":title, :description, :organizer, :format, :start_time, :duration, "
        ":address, :city, :country, :latitude, :longitude, :tags, :contact_email, "
        ":contact_phone, :contact_website, :primary_image_url, :gallery_urls, :video_url)"
        );

    // Привязка значений через геттеры
    query.bindValue(":title", QString::fromStdString(event.getTitle()));
    query.bindValue(":description", QString::fromStdString(event.getDescription()));
    query.bindValue(":organizer", QString::fromStdString(event.getOrganizer()));
    query.bindValue(":format", event.getFormat() == Event::Format::Online ? "Online" : "Offline");

    // Преобразование времени
    std::tm startTm = event.getStartTime();
    QDateTime startQDateTime = QDateTime::fromSecsSinceEpoch(std::mktime(&startTm));
    query.bindValue(":start_time", startQDateTime.toString(Qt::ISODate));

    std::tm durationTm = event.getDuration();
    QTime durationTime(durationTm.tm_hour, durationTm.tm_min, durationTm.tm_sec);
    query.bindValue(":duration", durationTime.toString("HH:mm:ss"));

    // Локация
    Location loc = event.getLocation();
    query.bindValue(":address", QString::fromStdString(loc.address));
    query.bindValue(":city", QString::fromStdString(loc.city));
    query.bindValue(":country", QString::fromStdString(loc.country));
    query.bindValue(":latitude", loc.coordinates.latitude);
    query.bindValue(":longitude", loc.coordinates.longitude);

    // Теги
    //QString tags = QString::fromStdString(boost::algorithm::join(event.getTags(), ","));
    QString tags = joinStrings(event.getTags(), ",");
    query.bindValue(":tags", tags);

    // Контакты
    ContactInfo contacts = event.getContacts();
    query.bindValue(":contact_email", QString::fromStdString(contacts.email));
    query.bindValue(":contact_phone", QString::fromStdString(contacts.phone));
    query.bindValue(":contact_website", QString::fromStdString(contacts.website));

    // Медиа
    MediaContent media = event.getMedia();
    query.bindValue(":primary_image_url", QString::fromStdString(media.primaryImageUrl));
    QString galleryUrls = joinStrings(media.galleryUrls, ",");
    query.bindValue(":gallery_urls", galleryUrls);
    query.bindValue(":video_url", QString::fromStdString(media.videoUrl));

    if (!query.exec()) {
        qCritical() << "Failed to add event:" << query.lastError().text();
        return false;
    }
    return true;
}

std::vector<Event> QEventDatabase::getEventsByFilters(
    Event::Format format,
    const std::string& city,
    const GeoCoordinates& userLocation,
    double radiusKm,
    const std::vector<std::string>& tags) const
{
    QMutexLocker locker(&dbMutex);
    std::vector<Event> events;
    QSqlQuery query(db);

    QString sql = "SELECT * FROM events WHERE 1=1";

    // Формат
    sql += QStringLiteral(" AND format = '") +
           (format == Event::Format::Online ? QStringLiteral("Online") : QStringLiteral("Offline")) +
           QStringLiteral("'");
    //sql += " AND format = '" + (format == Event::Format::Online ? "Online" : "Offline") + "'";

    // Город
    if (!city.empty()) {
        sql += " AND city = '" + QString::fromStdString(city) + "'";
    }

    // Радиус поиска
    if (radiusKm > 0) {
        sql += QString(" AND (6371 * acos("
                       "cos(radians(%1)) * cos(radians(latitude)) * "
                       "cos(radians(longitude) - radians(%2)) + "
                       "sin(radians(%1)) * sin(radians(latitude))) <= %3")
                   .arg(userLocation.latitude)
                   .arg(userLocation.longitude)
                   .arg(radiusKm);
    }

    // Теги
    for (const auto& tag : tags) {
        sql += " AND tags LIKE '%" + QString::fromStdString(tag) + "%'";
    }

    if (!query.exec(sql)) {
        qWarning() << "Filter error:" << query.lastError().text();
        return events;
    }

    while (query.next()) {
        events.push_back(parseEventFromQuery(query));
    }

    return events;
}

Event QEventDatabase::parseEventFromQuery(const QSqlQuery& query) const {
    // Парсинг данных из запроса
    std::string title = query.value("title").toString().toStdString();
    std::string description = query.value("description").toString().toStdString();
    std::string organizer = query.value("organizer").toString().toStdString();
    Event::Format format = query.value("format").toString() == "Online" ? Event::Format::Online : Event::Format::Offline;

    // Время начала
    QDateTime startQDateTime = QDateTime::fromString(query.value("start_time").toString(), Qt::ISODate);
    std::tm startTime = {};
    startTime.tm_year = startQDateTime.date().year() - 1900;
    startTime.tm_mon = startQDateTime.date().month() - 1;
    startTime.tm_mday = startQDateTime.date().day();
    startTime.tm_hour = startQDateTime.time().hour();
    startTime.tm_min = startQDateTime.time().minute();
    startTime.tm_sec = startQDateTime.time().second();

    // Продолжительность
    QTime durationTime = QTime::fromString(query.value("duration").toString(), "HH:mm:ss");
    std::tm duration = {};
    duration.tm_hour = durationTime.hour();
    duration.tm_min = durationTime.minute();
    duration.tm_sec = durationTime.second();

    // Локация
    Location location;
    location.address = query.value("address").toString().toStdString();
    location.city = query.value("city").toString().toStdString();
    location.country = query.value("country").toString().toStdString();
    location.coordinates.latitude = query.value("latitude").toDouble();
    location.coordinates.longitude = query.value("longitude").toDouble();

    // Теги
    std::vector<std::string> eventTags;
    QStringList tagsList = query.value("tags").toString().split(',');
    for (const QString& tag : tagsList) {
        eventTags.push_back(tag.trimmed().toStdString());
    }

    // Контакты
    ContactInfo contacts;
    contacts.email = query.value("contact_email").toString().toStdString();
    contacts.phone = query.value("contact_phone").toString().toStdString();
    contacts.website = query.value("contact_website").toString().toStdString();

    // Медиа
    MediaContent media;
    media.primaryImageUrl = query.value("primary_image_url").toString().toStdString();
    QStringList galleryUrls = query.value("gallery_urls").toString().split(',');
    for (const QString& url : galleryUrls) {
        media.galleryUrls.push_back(url.trimmed().toStdString());
    }
    media.videoUrl = query.value("video_url").toString().toStdString();

    // Создание объекта Event
    return Event(
        title,
        description,
        organizer,
        format,
        startTime,
        duration,
        location,
        eventTags,
        contacts,
        media
        );
}

double QEventDatabase::calculateDistance(const GeoCoordinates& a, const GeoCoordinates& b) {
    const double PI = 3.14159265358979323846;
    const double R = 6371.0;

    double lat1 = a.latitude * PI / 180.0;
    double lat2 = b.latitude * PI / 180.0;
    double dLat = (b.latitude - a.latitude) * PI / 180.0;
    double dLon = (b.longitude - a.longitude) * PI / 180.0;

    double hav = sin(dLat / 2) * sin(dLat / 2) +
                 cos(lat1) * cos(lat2) *
                     sin(dLon / 2) * sin(dLon / 2);
    double c = 2 * atan2(sqrt(hav), sqrt(1 - hav));

    return R * c;
}

