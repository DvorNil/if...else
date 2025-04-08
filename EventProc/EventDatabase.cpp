#include "EventDatabase.h"
#include <chrono>
#include <ctime>

EventDatabase& EventDatabase::getInstance() {
    static EventDatabase instance;
    return instance;
}

void EventDatabase::addEvent(const Event& event) {
    std::lock_guard<std::mutex> lock(dbMutex);
    events.push_back(event);
}

void EventDatabase::updateEvent(const std::string& eventTitle, const Event& newData) {
    std::lock_guard<std::mutex> lock(dbMutex);
    auto it = std::find_if(events.begin(), events.end(),
        [&](const Event& e) { return e.getTitle() == eventTitle; });

    if (it != events.end()) {
        *it = newData;
    }
}

void EventDatabase::deleteEvent(const std::string& eventTitle) {
    std::lock_guard<std::mutex> lock(dbMutex);
    events.erase(std::remove_if(events.begin(), events.end(),
        [&](const Event& e) { return e.getTitle() == eventTitle; }),
        events.end());
}

std::vector<Event> EventDatabase::getEventsByFilters(
    Event::Format format,
    const std::string& city,
    const GeoCoordinates& userLocation,
    double radiusKm,
    const std::vector<std::string>& tags) const
{
    std::vector<Event> result;
    std::lock_guard<std::mutex> lock(dbMutex);

    auto now = std::chrono::system_clock::to_time_t(
        std::chrono::system_clock::now());

    for (const auto& event : events) {
        // Фильтр по формату
        if (event.getFormat() != format) continue;

        // Фильтр по городу
        if (!city.empty() && event.getLocation().city != city) continue;

        // Фильтр по радиусу
        if (radiusKm > 0 && !isInRadius(event, userLocation, radiusKm)) continue;

        // Фильтр по тегам
        bool hasAllTags = true;
        for (const auto& tag : tags) {
            if (std::find(event.getTags().begin(),
                event.getTags().end(), tag) == event.getTags().end()) {
                hasAllTags = false;
                break;
            }
        }
        if (!hasAllTags) continue;

        result.push_back(event);
    }

    return result;
}

bool dataLessThanData(const std::tm& date1, const std::tm& date2) {
    std::time_t time1 = std::mktime(const_cast<std::tm*>(&date1));
    std::time_t time2 = std::mktime(const_cast<std::tm*>(&date2));
    return time1 < time2;
}

void EventDatabase::sortEvents(std::vector<Event>& events,
    SortBy criteria,
    const GeoCoordinates& referencePoint) const
{
    switch (criteria) {
    case SortBy::Date:
        std::sort(events.begin(), events.end(),
            [](const Event& a, const Event& b) {
                return  dataLessThanData(a.getStartTime(), b.getStartTime());
            });
        break;

    case SortBy::Distance:
        std::sort(events.begin(), events.end(),
            [&](const Event& a, const Event& b) {
                return calculateDistance(a.getLocation().coordinates, referencePoint) <
                    calculateDistance(b.getLocation().coordinates, referencePoint);
            });
        break;

    case SortBy::Title:
        std::sort(events.begin(), events.end(),
            [](const Event& a, const Event& b) {
                return a.getTitle() < b.getTitle();
            });
        break;
    }
}

double EventDatabase::calculateDistance(const GeoCoordinates& a,
    const GeoCoordinates& b) const
{
    const double PI = 3.14159265358979;
    // Формула гаверсинусов
    constexpr double R = 6371.0; // Земной радиус в км
    const double lat1 = a.latitude * PI / 180.0;
    const double lat2 = b.latitude * PI / 180.0;
    const double dLat = (b.latitude - a.latitude) * PI / 180.0;
    const double dLon = (b.longitude - a.longitude) * PI / 180.0;

    const double h = sin(dLat / 2) * sin(dLat / 2) +
        cos(lat1) * cos(lat2) *
        sin(dLon / 2) * sin(dLon / 2);

    return 2 * R * asin(sqrt(h));
}

bool EventDatabase::isInRadius(const Event& event,
    const GeoCoordinates& center,
    double radius) const
{
    return calculateDistance(event.getLocation().coordinates, center) <= radius;
}