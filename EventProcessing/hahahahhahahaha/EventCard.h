#pragma once
#include "Structures.h"
#include "Event.h"

class EventCard {
public:
    explicit EventCard(const Event& event);

    std::string renderTooltip() const;
    std::string getTooltip() const;
    std::string renderFullCard() const;
    std::string getFullCard() const;

private:
    const Event& event;

    static std::string truncate(const std::string& text, size_t length);
    static std::string formatToString(Event::Format format);
    std::string formatDateTime(const std::tm& startTime, const std::tm& duration) const;
    std::string formatLocationInfo() const;
    std::string formatOrganizerInfo() const;
    std::string getPreviewImage() const;
    std::string joinTags() const;
};