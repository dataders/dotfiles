// Lofi Girl — Approach A overlay shader
// Pairs with background-image = lofi-girl.gif (or .png)
// Adds: warm color tint, film grain, soft vignette
// Keep effects subtle — terminal readability first.

#define GRAIN_STRENGTH  0.045
#define WARMTH          0.06    // amber push: 0=off, 0.10=noticeable
#define VIGNETTE        0.35

float hash(vec2 p) {
    p = fract(p * vec2(234.56, 789.01));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord.xy / iResolution.xy;
    vec4 term = texture(iChannel0, uv);

    // Warm tint: nudge reds/greens up, keep blue where it is
    vec3 col = term.rgb;
    col.r = clamp(col.r + WARMTH * 0.8, 0.0, 1.0);
    col.g = clamp(col.g + WARMTH * 0.3, 0.0, 1.0);

    // Film grain — flickers with time so it feels alive
    float grain = hash(uv + fract(iTime * 0.07)) * 2.0 - 1.0;
    col += grain * GRAIN_STRENGTH;

    // Corner vignette
    vec2 c = abs(uv * 2.0 - 1.0);
    vec2 edge = clamp((c - 0.60) / 0.40, 0.0, 1.0);
    float vignette = 1.0 - edge.x * edge.y * VIGNETTE;
    col *= vignette;

    fragColor = vec4(clamp(col, 0.0, 1.0), term.a);
}
