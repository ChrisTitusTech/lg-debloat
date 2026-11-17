// Home only. Other keys continue through LG's original filter chain.
var minimalHomePressedAt = 0;
function handleMinimalHome(key, pressed, autoRepeat) {
    try {
        if (key !== Qt.Key_Super_L) return KeyPolicy.NextPolicy;
        if (pressed) {
            if (!autoRepeat) minimalHomePressedAt = Date.now();
        } else {
            var held = minimalHomePressedAt && Date.now() - minimalHomePressedAt >= 1500;
            minimalHomePressedAt = 0;
            applicationManager.launch(held ? 'com.webos.app.home' : 'org.example.minimalhome',
                JSON.stringify({activateType: 'home', launchType: 'homeKey'}));
        }
        return KeyPolicy.Accepted;
    } catch (e) {
        return KeyPolicy.NextPolicy;
    }
}
