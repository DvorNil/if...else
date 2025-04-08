#pragma once

#include "Libraries.h"

struct GeoCoordinates {
    double latitude;
    double longitude;
};
struct Location {
    std::string address;
    std::string city;
    std::string country;
    GeoCoordinates coordinates;
};
struct ContactInfo {
    std::string email;
    std::string phone;
    std::string website;

    std::string toString() const 
    {
        return "Email: " + email + "\n" + "Phone: " + phone + "\n" + "Website: " + website;
    };
};
struct MediaContent {
    std::string primaryImageUrl;
    std::vector<std::string> galleryUrls;
    std::string videoUrl;
};