document.addEventListener('DOMContentLoaded', function () {
  function updateVisibility() {
    var platformEl = document.querySelector('#id_platform');
    if (!platformEl) return;
    var platform = platformEl.value;
    var iosSections = document.querySelectorAll('.ios-config');
    var androidSections = document.querySelectorAll('.android-config');

    if (platform === 'ios') {
      iosSections.forEach(function (e) { e.style.display = ''; });
      androidSections.forEach(function (e) { e.style.display = 'none'; });
    } else if (platform === 'android') {
      iosSections.forEach(function (e) { e.style.display = 'none'; });
      androidSections.forEach(function (e) { e.style.display = ''; });
    } else {
      iosSections.forEach(function (e) { e.style.display = ''; });
      androidSections.forEach(function (e) { e.style.display = ''; });
    }
  }

  updateVisibility();
  var platformEl = document.querySelector('#id_platform');
  if (platformEl) {
    platformEl.addEventListener('change', updateVisibility);
  }
});

