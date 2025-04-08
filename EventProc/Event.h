#pragma once
#include "Structures.h"
#include "Libraries.h"

class Event
{
public:
    enum class Format { Online, Offline};

    Event(std::string title, std::string description, std::string organizer,
        Format format, std::tm startTime, std::tm duration,
        Location location, std::vector<std::string> tags,
        ContactInfo contacts, MediaContent media)
        : title(std::move(title)),
        description(std::move(description)),
        organizer(std::move(organizer)),
        format(format),
        startTime(startTime),
        duration(duration),
        location(std::move(location)),
        tags(std::move(tags)),
        contacts(std::move(contacts)),
        media(std::move(media)) {}

    // �������
    const std::string& getTitle() const { return title; }
    const std::string& getDescription() const { return description; }
    const std::string& getOrganizer() const { return organizer; }
    Format getFormat() const { return format; }
    const std::tm& getStartTime() const { return startTime; }
    const std::tm& getDuration() const { return duration; }
    const Location& getLocation() const { return location; }
    const std::vector<std::string>& getTags() const { return tags; }
    const ContactInfo& getContacts() const { return contacts; }
    const MediaContent& getMedia() const { return media; }

private:
    std::string title;
    std::string description;
    std::string organizer;
    Format format;
    std::tm startTime;
    std::tm duration;
    Location location;
    std::vector<std::string> tags;
    ContactInfo contacts;
    MediaContent media;
};

