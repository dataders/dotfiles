// transparent background
const bool transparent = false;

// only show stars where terminal content is dark (below this luminance)
const float threshold = 0.15;

// fewer grid divisions = fewer, sparser stars
const float repeats = 14.;

// fewer layers = simpler, less busy
const float layers = 8.;

// overall star brightness multiplier (keep low for subtlety)
const float brightness = 0.30;

// animation speed scale (lower = slower drift)
const float speed = 0.4;

const vec3 white = vec3(1.0);

float luminance(vec3 color) {
    return dot(color, vec3(0.2126, 0.7152, 0.0722));
}

float N21(vec2 p) {
    p = fract(p * vec2(233.34, 851.73));
    p += dot(p, p + 23.45);
    return fract(p.x * p.y);
}

vec2 N22(vec2 p) {
    float n = N21(p);
    return vec2(n, N21(p + n));
}

mat2 scale(vec2 _scale) {
    return mat2(_scale.x, 0.0, 0.0, _scale.y);
}

vec3 stars(vec2 uv, float offset) {
    float timeScale = -(iTime * speed + offset) / layers;
    float trans = fract(timeScale);
    float newRnd = floor(timeScale);
    vec3 col = vec3(0.);

    uv -= vec2(0.5);
    uv = scale(vec2(trans)) * uv;
    uv += vec2(0.5);

    uv.x *= iResolution.x / iResolution.y;
    uv *= repeats;

    vec2 ipos = floor(uv);
    uv = fract(uv);

    vec2 rndXY = N22(newRnd + ipos * (offset + 1.)) * 0.9 + 0.05;
    float rndSize = N21(ipos) * 100. + 200.;

    vec2 j = (rndXY - uv) * rndSize;
    float sparkle = 1. / dot(j, j);

    col += white * sparkle;
    col *= smoothstep(1., 0.8, trans);
    return col;
}

void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    vec2 uv = fragCoord / iResolution.xy;
    vec3 col = vec3(0.);

    for (float i = 0.; i < layers; i++) {
        col += stars(uv, i);
    }

    vec4 terminalColor = texture(iChannel0, uv);
    float mask = 1.0 - step(threshold, luminance(terminalColor.rgb));
    vec3 blendedColor = mix(terminalColor.rgb, col * brightness, mask);

    fragColor = vec4(blendedColor, terminalColor.a);
}
