var homeBackgrounds = [
  {
    "title": "Alaska lake sunset",
    "file": "backgrounds/sunset-lake-tetlin-national-wildlife-refuge.jpg"
  },
  {
    "title": "Mountain vista",
    "file": "backgrounds/scenic-mountains.jpg"
  },
  {
    "title": "Smoky Mountains",
    "file": "backgrounds/scenic-view-great-smokey-mountains-national-park.jpg"
  },
  {
    "title": "Desert panorama",
    "file": "backgrounds/desert-panorama.jpg"
  },
  {
    "title": "Kofa desert mountains",
    "file": "backgrounds/kofa-national-wildlife-refuge-landscape.jpg"
  },
  {
    "title": "Baca mountain landscape",
    "file": "backgrounds/mountain-scenic.jpg"
  },
  {
    "title": "Cabeza Prieta desert",
    "file": "backgrounds/desert-landscape.jpg"
  }
];
function homeBackgroundForDate(d) {
 var day=Math.floor((Date.UTC(d.getFullYear(),d.getMonth(),d.getDate())-Date.UTC(2026,10,17))/86400000);
 return homeBackgrounds[((day%homeBackgrounds.length)+homeBackgrounds.length)%homeBackgrounds.length];
}
