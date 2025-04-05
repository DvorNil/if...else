#pragma once
#include "EventCard.h"


EventCard::EventCard(const Event& event) : event(event) {}

std::string EventCard::renderTooltip() const {
    std::stringstream ss;
    ss << "<div class=\"event-tooltip\">\n"
        << "  <h3>" << event.getTitle() << "</h3>\n"
        << "  <p>" << truncate(event.getDescription(), 100) << "</p>\n"
        << "  <div class=\"meta\">\n"
        << "    <span class=\"format\">" << formatToString(event.getFormat()) << "</span>\n"
        << "    <span class=\"datetime\">" << formatDateTime(event.getStartTime(), event.getDuration()) << "</span>\n"
        << "  </div>\n"
        << "</div>";
    return ss.str();
}

std::string EventCard::getTooltip() const {
    std::stringstream ss;
    ss << event.getTitle() << "\n\n"
        << "Description: " << truncate(event.getDescription(), 100) << "\n\n"
        << "Format: " << formatToString(event.getFormat()) << "\n"
        << "Date: " << formatDateTime(event.getStartTime(), event.getDuration()) << "\n";
    return ss.str();
}

std::string EventCard::renderFullCard() const {
    std::stringstream ss;
    ss << "<article class=\"event-card\">\n"
        << "  <header>\n"
        << "    <img src=\"" << getPreviewImage() << "\" alt=\"" << event.getTitle() << "\">\n"
        << "    <h2>" << event.getTitle() << "</h2>\n"
        << "  </header>\n"
        << "  <div class=\"content\">\n"
        << "    <p class=\"description\">" << event.getDescription() << "</p>\n"
        << "    <div class=\"details\">\n"
        << "      <div class=\"organizer\">" << formatOrganizerInfo() << "</div>\n"
        << "      <div class=\"location\">" << formatLocationInfo() << "</div>\n"
        << "      <div class=\"tags\">" << joinTags() << "</div>\n"
        << "    </div>\n"
        << "  </div>\n"
        << "</article>";
    return ss.str();
}

std::string EventCard::getFullCard() const {
    std::stringstream ss;
    ss << event.getTitle() << "\n\n"
        << getPreviewImage() << "\n\n"
        << "Description:\n" << event.getDescription() << "\n\n"
        << "Organizer: " << formatOrganizerInfo() << "\n"
        << "Location: " << formatLocationInfo() << "\n"
        << "Tags: " << joinTags() << "\n";
    return ss.str();
}

std::string EventCard::truncate(const std::string& text, size_t length) {
    return (text.length() > length) ? text.substr(0, length - 3) + "..." : text;
}

std::string EventCard::formatToString(Event::Format format) {
    return (format == Event::Format::Online) ? "Online" : "Offline";
}

std::string EventCard::formatDateTime(const std::tm& startTime, const std::tm& duration) const {
    std::stringstream ss;
    ss << std::put_time(&startTime, "%d.%m.%Y %H:%M") << " ("
        << std::setfill('0') << std::setw(2) << duration.tm_hour << "h "
        << std::setw(2) << duration.tm_min << "m)";
    return ss.str();
}

std::string EventCard::formatLocationInfo() const {
    const auto& loc = event.getLocation();
    return (event.getFormat() == Event::Format::Online)
        ? "Online event (Host: " + loc.city + ")"
        : loc.address + ", " + loc.city + ", " + loc.country;
}

std::string EventCard::formatOrganizerInfo() const {
    return event.getOrganizer() + "\n" + event.getContacts().toString();
}

std::string EventCard::getPreviewImage() const {
    const auto& media = event.getMedia();
    return media.primaryImageUrl.empty() ? "default-image.jpg" : media.primaryImageUrl;
}

std::string EventCard::joinTags() const {
    std::string result;
    for (const auto& tag : event.getTags()) {
        if (!result.empty()) result += ", ";
        result += tag;
    }
    return result;
}