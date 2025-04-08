#pragma once
#ifndef QEVENTDATABASE_H
#define QEVENTDATABASE_H

#include <QMainWindow>
#include <QObject>
#include <QQuickItem>
#include <QWidget>
#include "Event.h"
#include "Structures.h"
#include "Libraries.h"
#include <QSqlDatabase>
#include <QSqlQuery>
#include <QSqlError>
#include <QMutex>

class QEventDatabase {
public:
    static QEventDatabase& getInstance();

    // Основные операции с БД
    bool addEvent(const Event& event);
    bool updateEvent(const std::string& eventTitle, const Event& newData);
    bool deleteEvent(const std::string& eventTitle);

    // Фильтрация и сортировка
    std::vector<Event> getEventsByFilters(
        Event::Format format,
        const std::string& city = "",
        const GeoCoordinates& userLocation = {0,0},
        double radiusKm = 0,
        const std::vector<std::string>& tags = {}
        ) const;

    enum class SortBy { Date, Distance, Title };

    // Вспомогательные методы
    static double calculateDistance(const GeoCoordinates& a, const GeoCoordinates& b);

private:
    QEventDatabase();
    QEventDatabase(const QEventDatabase&) = delete;
    QEventDatabase& operator=(const QEventDatabase&) = delete;

    QSqlDatabase db;
    mutable QMutex dbMutex;

    // Внутренние методы
    bool initDatabase();
    Event parseEventFromQuery(const QSqlQuery& query) const;
    QString buildBaseQuery() const;
    bool isInRadius(const Event& event, const GeoCoordinates& center, double radius) const;
};

#endif
