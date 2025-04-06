#pragma once
#include "Event.h"
#include "Structures.h"
#include "Libraries.h"

class EventDatabase {
public:
    static EventDatabase& getInstance();

    void addEvent(const Event& event);
    void updateEvent(const std::string& eventTitle, const Event& newData);
    void deleteEvent(const std::string& eventTitle);

    std::vector<Event> getEventsByFilters(
        Event::Format format,
        const std::string& city = "",
        const GeoCoordinates& userLocation = { 0,0 },
        double radiusKm = 0,
        const std::vector<std::string>& tags = {}
    ) const;

    enum class SortBy { Date, Distance, Title };
    void sortEvents(std::vector<Event>& events, SortBy criteria,
        const GeoCoordinates& referencePoint = { 0,0 }) const;
    

    // Вспомогательные методы (В public для тестов)
    double calculateDistance(const GeoCoordinates& a,
        const GeoCoordinates& b) const;
    bool isInRadius(const Event& event,
        const GeoCoordinates& center,
        double radius) const;
private:
    EventDatabase() = default;
    EventDatabase(const EventDatabase&) = delete;
    EventDatabase& operator=(const EventDatabase&) = delete;

    std::vector<Event> events;
    mutable std::mutex dbMutex;


};