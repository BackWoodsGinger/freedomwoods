"use strict";

/**
 * Animates the tech jumbotron track: scrolls left slowly (content moves left)
 * using requestAnimationFrame. Only runs when #techJumbotronTrack exists.
 */
(function () {
    function init() {
        var track = document.getElementById("techJumbotronTrack");
        if (!track) return;

        var items = track.querySelectorAll(".tech-jumbotron-logo");
        if (items.length === 0) items = track.children;
        var half = Math.floor(items.length / 2);
        var singleSetWidth = 0;
        var position = 0;
        var speed = 0.35; /* pixels per frame — slow leftward scroll */

        function measureSetWidth() {
            var total = 0;
            for (var i = 0; i < half; i++) {
                var el = items[i];
                if (!el) break;
                var style = getComputedStyle(el);
                total += el.offsetWidth + (parseFloat(style.marginRight) || 0);
            }
            singleSetWidth = total;
            return total;
        }

        function tick() {
            position -= speed;
            if (singleSetWidth > 0 && position <= -singleSetWidth) {
                position += singleSetWidth;
            }
            track.style.transform = "translate3d(" + position + "px, 0, 0)";
            requestAnimationFrame(tick);
        }

        function startScroll() {
            var w = measureSetWidth();
            if (w <= 0) singleSetWidth = Math.max(400, (track.offsetWidth || 800) / 2);
            requestAnimationFrame(tick);
        }

        if (document.readyState === "complete") {
            startScroll();
        } else {
            window.addEventListener("load", startScroll);
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
