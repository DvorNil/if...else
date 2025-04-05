#include "Libraries.h"
#include "Event.h"
#include "EventCard.h"
#include "EventDatabase.h"

using namespace std;

void testEventCard();
void testEventDatabase();

int main()
{
    setlocale(LC_ALL, "Russian");
    testEventDatabase();
    return 0;
}

void testEventCard() {
    //std::ofstream fout ("index.html");
        // Пример использования
    std::tm startTime = {};
    startTime.tm_year = 125; // 2025 - 1900
    startTime.tm_mon = 4;    // May (0-based)
    startTime.tm_mday = 15;
    startTime.tm_hour = 10;

    std::tm duration = {};
    duration.tm_hour = 8;

    Event aiConference(
        "AI Tech Summit 2025",
        "Международная конференция по искусственному интеллекту...",
        "AI Research Foundation",
        Event::Format::Online,
        startTime,
        duration,
        { "", "Москва", "", {} },
        { "конференция", "AI", "онлайн" },
        { "contact@airesearch.org", "", "https://airesearch.org/summit" },
        { "/images/ai-summit.jpg", {}, "" }
    );

    EventCard card(aiConference);
    cout << card.getTooltip() << "\n\n";
    cout << card.getFullCard() << std::endl;

}


// Функция для вывода информации о мероприятии
void printEvent(const Event& event, const GeoCoordinates& reference = { 0,0 }) {
    EventCard card (event);
    cout << "=======================\n";
    cout << card.getFullCard();
    cout << "=======================\n";
}

void testEventDatabase() {
    // Инициализация базы данных
    EventDatabase& db = EventDatabase::getInstance();
    tm start1 = {};
    start1.tm_year = 125; // 2025
    start1.tm_mon = 4;    // май (0-based)
    start1.tm_mday = 20;
    start1.tm_hour = 10;

    tm start2 = {};
    start2.tm_year = 125;
    start2.tm_mon = 5;    // июнь
    start2.tm_mday = 15;
    start2.tm_hour = 14;
    start2.tm_min = 30;

    tm start3 = {};
    start3.tm_year = 125;
    start3.tm_mon = 6;    // июль
    start3.tm_mday = 10;
    start3.tm_hour = 11;

    tm start4 = {};
    start4.tm_year = 125;
    start4.tm_mon = 4;    // май
    start4.tm_mday = 25;
    start4.tm_hour = 15;

    tm start5 = {};
    start5.tm_year = 125;
    start5.tm_mon = 5;    // июнь
    start5.tm_mday = 5;
    start5.tm_hour = 19;

    tm duration = {};
    duration.tm_hour = 8;

    tm duration2 = {};
    duration2.tm_hour = 2;

    // Тестовые мероприятия
    Event events[] = {
        {
            "IT Хакатон 2025",
            "Главный хакатон года для разработчиков",
            "IT Community",
            Event::Format::Online,
            start1,
            duration,
            {"", "Москва", "Россия", {55.7558, 37.6176}},
            {"хакатон", "программирование", "онлайн"},
            {"hack@it.ru", "+7 999 123-45-67", "https://hack.it.ru"},
            {"/images/hack.jpg"}
        },
        {
            "AI Конференция",
            "Конференция по искусственному интеллекту",
            "AI Labs",
            Event::Format::Offline,
            start2,
            duration,
            {"Невский пр. 123", "Санкт-Петербург", "Россия", {59.9343, 30.3351}},
            {"конференция", "AI", "офлайн"},
            {"conf@ai.ru", "", "https://ai-conf.ru"},
            {"/images/ai-conf.jpg"}
        },
        {
            "Цифровая выставка",
            "Современные технологии в промышленности",
            "TechExpo",
            Event::Format::Offline,
            start3,
            duration,
            {"Кремлевская 35", "Казань", "Россия", {55.7961, 49.1064}},
            {"выставка", "технологии", "офлайн"},
            {"expo@tech.ru", "+7 843 555-44-33", "https://techexpo.ru"},
            {"/images/expo.jpg"}
        },
        {
            "Онлайн-семинар по DevOps",
            "Практики DevOps для современных проектов",
            "Cloud Masters",
            Event::Format::Online,
            start4,
            duration,
            {"", "Новосибирск", "Россия", {55.0084, 82.9357}},
            {"семинар", "DevOps", "онлайн"},
            {"devops@cloud.ru", "", "https://cloudmasters.ru"},
            {"/images/devops.jpg"}
        },
        {
            "Митап разработчиков",
            "Ежемесячная встреча московских разработчиков",
            "Moscow Devs",
            Event::Format::Offline,
            start5,
            duration2,
            {"Ленинградский пр. 47", "Москва", "Россия", {55.8037, 37.5356}},
            {"митап", "нетворкинг", "офлайн"},
            {"meetup@mdev.ru", "+7 495 123-45-67", "https://moscowdevs.ru"},
            {"/images/meetup.jpg"}
        }
    };

    // Добавление мероприятий в базу
    for (const auto& event : events) {
        db.addEvent(event);
    }

    // Тестирование фильтров
    cout << "=== Все онлайн-мероприятия ===\n";
    auto onlineEvents = db.getEventsByFilters(Event::Format::Online);
    for (const auto& e : onlineEvents) printEvent(e);

    // Точка отсчета - Москва
    GeoCoordinates moscow = { 55.7558, 37.6176 };

    cout << "\n=== Офлайн мероприятия в радиусе 500 км от Москвы ===\n";
    auto nearbyEvents = db.getEventsByFilters(
        Event::Format::Offline,
        "",  // любой город
        moscow,
        500  // радиус 500 км
    );
    db.sortEvents(nearbyEvents, EventDatabase::SortBy::Distance, moscow);
    for (const auto& e : nearbyEvents) printEvent(e, moscow);

    // События с тегом "конференция"
    cout << "\n=== Мероприятия с тегом 'конференция' ===\n";
    auto conferenceEvents = db.getEventsByFilters(
        Event::Format::Offline,
        "",
        { 0,0 },
        0,
        { "конференция" }
    );
    for (const auto& e : conferenceEvents) printEvent(e);
}