/**
 * Built-in content prompts for style-LoRA training sets. Prompts describe only
 * subject, appearance, coloured clothing, framing, pose, setting and lighting; never
 * artist, medium or quality tags, so captions stay content-only and the trained LoRA
 * absorbs the style.
 */

export interface DatasetCategory {
  id: string
  label: string
  description: string
}

export interface DatasetPrompt {
  id: string
  category: string
  prompt: string
}

export const DATASET_CATEGORIES: readonly DatasetCategory[] = [
  { id: 'portrait', label: '特写与表情', description: '脸部和肩部以上，覆盖多种表情与角度' },
  { id: 'upper', label: '半身日常', description: '上半身构图，日常动作与服装' },
  { id: 'full', label: '全身与动作', description: '全身构图，站坐跑跳等姿势' },
  { id: 'scene', label: '人物与场景', description: '人物较小、环境占比大的远景' },
  { id: 'light', label: '光照与时段', description: '逆光、夜景、室内暖光等光照条件' },
  { id: 'multi', label: '多人互动', description: '两人及以上的构图与互动' },
  { id: 'boy', label: '男孩（年幼）', description: '年幼男孩的日常场景；仅限健全内容，不可搭配身体描写类画风' },
  { id: 'nohuman', label: '无人物', description: '风景、建筑、静物与动物' },
]

// Every person prompt names hair, eyes and coloured clothing so the generated image
// and its caption describe the same things (operator, 2026-10-31).
const PROMPTS: Record<string, readonly string[]> = {
  portrait: [
    '1girl, solo, portrait, looking at viewer, smile, long hair, black hair, brown eyes, white collared shirt, simple background',
    '1girl, solo, close-up, face, closed eyes, peaceful, short hair, blonde hair, light blue sweater',
    '1girl, solo, portrait, from side, profile, ponytail, brown hair, green eyes, gold earrings, navy blue jacket, looking away',
    '1girl, solo, close-up, open mouth, laughing, twintails, pink hair, purple eyes, red hair ribbon, white blouse',
    '1girl, solo, portrait, crying, tears, sad, wavy hair, silver hair, blue eyes, black turtleneck',
    '1girl, solo, portrait, blush, embarrassed, hand on own cheek, bob cut, brown hair, amber eyes, beige cardigan',
    '1girl, solo, portrait, from below, looking down, long hair, silver hair, red eyes, white hair flower, black dress',
    '1girl, solo, portrait, from above, looking up, surprised, short hair, black hair, green eyes, yellow hoodie',
    '1girl, solo, portrait, wink, tongue out, peace sign, side ponytail, orange hair, blue eyes, pink t-shirt',
    '1girl, solo, close-up, half-closed eyes, sleepy, messy hair, light brown hair, grey eyes, light blue pajamas',
    '1girl, solo, portrait, straw hat, smile, looking at viewer, long hair, blonde hair, blue eyes, white sundress, outdoors',
    '1girl, solo, portrait, hand on own chin, thinking, round eyewear, braid, dark green hair, brown eyes, grey vest, white shirt',
    '1girl, solo, portrait, three-quarter view, looking back, very long hair, blue hair, yellow eyes, white kimono',
    '1girl, solo, close-up, covering mouth, giggling, cat ears, short hair, white hair, pink eyes, white blouse, red scarf',
    '1boy, solo, portrait, looking at viewer, serious, short hair, brown hair, brown eyes, white collared shirt, white background',
    '1boy, solo, portrait, smirk, glasses, short hair, black hair, grey eyes, black sweater, gradient background',
  ],
  upper: [
    '1girl, solo, upper body, school uniform, navy blue serafuku, white sailor collar, red neckerchief, holding book, long hair, black hair, brown eyes, classroom',
    '1girl, solo, upper body, drinking, holding cup, coffee, cream sweater, short hair, brown hair, green eyes, cafe, sitting',
    '1girl, solo, upper body, waving, smile, grey hoodie, ponytail, blonde hair, blue eyes, street',
    '1girl, solo, upper body, arms up, stretching, white tank top, short hair, pink hair, purple eyes, bedroom, morning',
    '1girl, solo, upper body, maid, black dress, white apron, white maid headdress, holding tray, long hair, brown hair, blue eyes, indoors',
    '1girl, solo, upper body, holding umbrella, transparent umbrella, yellow raincoat, rain, looking up, short hair, black hair, brown eyes',
    '1girl, solo, upper body, red kimono, floral print, holding folding fan, smile, hair bun, black hair, red eyes',
    '1girl, solo, upper body, eating, holding ice cream, white t-shirt, twintails, light brown hair, green eyes, summer',
    '1girl, solo, upper body, writing, holding pen, desk, notebook, white blouse, long hair, black hair, grey eyes',
    '1girl, solo, upper body, arms crossed, pout, black leather jacket, red t-shirt, short hair, silver hair, yellow eyes',
    '1girl, solo, upper body, holding phone, looking at phone, light purple sweater, long hair, blue hair, blue eyes, sitting',
    '1girl, solo, upper body, hands on own hips, confident, green military uniform, peaked cap, short hair, blonde hair, red eyes',
    '1girl, solo, upper body, flower crown, holding flower, white dress, long hair, pink hair, green eyes',
    '1girl, solo, upper body, black witch hat, black cloak, holding wooden staff, magic, long hair, purple hair, yellow eyes',
    '1boy, solo, upper body, black suit, white shirt, blue necktie, adjusting necktie, short hair, black hair, brown eyes, office',
    '1boy, solo, upper body, silver armor, red cape, holding sword, serious, short hair, blonde hair, blue eyes',
  ],
  full: [
    '1girl, solo, full body, standing, school uniform, white shirt, red necktie, navy blue pleated skirt, white socks, brown loafers, long hair, black hair, simple background',
    '1girl, solo, full body, running, motion lines, blue track jacket, black shorts, white sneakers, ponytail, brown hair, track',
    '1girl, solo, full body, sitting, on chair, crossed legs, black dress, black heels, long hair, blonde hair, blue eyes, indoors',
    '1girl, solo, full body, dancing, spinning, light blue dress, white shoes, smile, short hair, orange hair, green eyes',
    '1girl, solo, full body, kneeling, praying, nun, black habit, white veil, silver hair, blue eyes, church',
    '1girl, solo, full body, lying, on back, grass, closed eyes, relaxing, white blouse, green skirt, long hair, brown hair',
    '1girl, solo, full body, squatting, petting cat, black cat, grey hoodie, blue jeans, white sneakers, short hair, pink hair, street',
    '1girl, solo, full body, standing on one leg, arms out, balancing, wall, yellow sundress, brown sandals, twintails, black hair',
    '1girl, solo, full body, sitting, on floor, hugging own knees, oversized white sweater, black shorts, long hair, silver hair, bedroom',
    '1girl, solo, full body, standing, beach, ocean, white one-piece swimsuit, long hair, blonde hair, blue eyes',
    '1girl, solo, full body, battle stance, silver armor, red cape, holding shield, holding sword, ponytail, red hair, green eyes',
    '1girl, solo, full body, ballerina, ballet, tiptoes, pink tutu, white tights, pink ballet slippers, hair bun, brown hair, stage',
    '1girl, solo, full body, riding bicycle, red bicycle, white blouse, blue skirt, straw hat, black hair, countryside, summer',
    '1boy, solo, full body, standing, hands in pockets, white t-shirt, blue jeans, white sneakers, short hair, brown hair, simple background',
    '1boy, solo, full body, jumping, midair, basketball, red jersey, black shorts, short hair, black hair, outdoors',
  ],
  scene: [
    '1girl, solo, wide shot, standing, field, flowers, blue sky, clouds, wind, white dress, long hair, brown hair',
    '1girl, solo, wide shot, sitting, bench, park, autumn, falling leaves, brown coat, red scarf, long hair, black hair',
    '1girl, solo, wide shot, walking, city street, crowd, buildings, crosswalk, beige trench coat, short hair, blonde hair',
    '1girl, solo, wide shot, library, tall bookshelves, ladder, reading, green cardigan, brown skirt, glasses, braid, dark brown hair',
    '1girl, solo, wide shot, forest, path, trees, sunlight filtering through trees, white blouse, brown backpack, short hair, orange hair',
    '1girl, solo, wide shot, snow, snowing, white winter coat, red mittens, footprints, long hair, black hair',
    '1girl, solo, wide shot, beach, waves, barefoot, holding sandals, light blue sundress, long hair, blonde hair',
    '1girl, solo, wide shot, shrine, torii, stone stairs, miko, white kimono, red hakama, long hair, black hair',
    '1girl, solo, wide shot, greenhouse, plants, holding watering can, green apron, white shirt, short hair, light brown hair',
    '1girl, solo, wide shot, castle, fantasy, courtyard, purple gown, silver tiara, long hair, silver hair',
    '1girl, solo, wide shot, underwater, bubbles, fish, floating, white dress, long hair, blue hair',
    '1girl, solo, wide shot, cafe interior, window seat, plants, sitting, mustard yellow sweater, short hair, black hair',
    '1girl, solo, wide shot, festival, food stall, lanterns, blue yukata, floral print, red obi, hair bun, black hair',
    '1boy, solo, wide shot, from behind, cliff, looking afar, mountains, dark green coat, short hair, black hair',
    '1boy, solo, wide shot, train station, platform, waiting, train, navy blue coat, grey scarf, short hair, brown hair',
  ],
  light: [
    '1girl, solo, upper body, backlighting, sunset, orange sky, silhouette, wind, white shirt, long hair, black hair',
    '1girl, solo, cowboy shot, night, city lights, bokeh, black coat, white scarf, short hair, silver hair',
    '1girl, solo, portrait, window, sunlight, light rays, curtains, indoors, light blue blouse, long hair, blonde hair',
    '1girl, solo, full body, moonlight, night sky, stars, field, white nightgown, long hair, blue hair',
    '1girl, solo, cowboy shot, neon lights, purple lighting, night, street, black jacket, twintails, pink hair',
    '1girl, solo, upper body, candlelight, dark room, holding candle, dark red dress, long hair, brown hair',
    '1girl, solo, portrait, dappled sunlight, leaves, shade, summer, white sundress, short hair, black hair',
    '1girl, solo, cowboy shot, overcast, rain, wet hair, grey sky, navy blue school uniform, long hair, brown hair',
    '1girl, solo, full body, blue hour, twilight, street lamp, beige coat, red scarf, short hair, blonde hair',
    '1girl, solo, upper body, fireworks, night, purple yukata, floral print, looking up, hair bun, black hair',
    '1boy, solo, upper body, campfire, night, warm light, sitting, brown jacket, short hair, black hair',
  ],
  multi: [
    '2girls, upper body, friends, smile, looking at viewer, navy blue blazer, white shirt, long hair, black hair, short hair, blonde hair',
    '2girls, sitting, bench, park, talking, eating, sandwich, pink sweater, grey hoodie, brown hair, silver hair',
    '3girls, group, full body, standing, smile, red dress, blue dress, yellow dress, black hair, brown hair, blonde hair, outdoors',
    '2girls, full body, dancing together, holding hands, stage, white dress, black dress, long hair, brown hair, short hair, black hair',
    '2girls, portrait, cheek-to-cheek, selfie, peace sign, white t-shirt, pink t-shirt, pink hair, blue hair',
    '2girls, full body, running, chasing, flowers, field, light blue dress, yellow dress, brown hair, black hair',
    '2boys, upper body, back-to-back, arms crossed, serious, black jacket, white jacket, short hair, black hair, silver hair',
  ],
  // Wholesome, fully clothed everyday scenes only; never combine with body-shape style tags.
  boy: [
    'male child, 1boy, solo, portrait, smile, looking at viewer, short hair, brown hair, brown eyes, white t-shirt, simple background',
    'male child, 1boy, solo, upper body, reading, holding book, white shirt, navy blue sweater vest, short hair, black hair, classroom',
    'male child, 1boy, solo, full body, running, park, red t-shirt, blue shorts, white sneakers, short hair, blonde hair, smile',
    'male child, 1boy, solo, full body, flying kite, holding string, green hoodie, khaki shorts, short hair, brown hair, blue sky, field',
    'male child, 1boy, solo, upper body, eating, holding ice cream, yellow t-shirt, short hair, black hair, smile, summer',
    'male child, 1boy, solo, full body, standing, rain, yellow raincoat, red backpack, green rain boots, short hair, black hair',
    'male child, 1boy, solo, upper body, drawing, holding crayon, desk, light blue shirt, short hair, brown hair, indoors',
    'male child, 1boy, solo, full body, playing with dog, golden retriever, white shirt, brown shorts, short hair, blonde hair, garden',
    'male child, 1boy, solo, portrait, surprised, open mouth, short hair, silver hair, blue eyes, dark blue hoodie',
    'male child, 1boy, solo, full body, snow, making snowman, grey winter coat, red scarf, blue mittens, short hair, brown hair',
    'male child, 1boy, solo, upper body, festival, holding cotton candy, blue jinbei, lanterns, night, short hair, black hair',
    'male child, 1boy, solo, full body, sitting, bench, reading picture book, orange sweater, brown pants, short hair, black hair',
    'male child, 1boy, solo, cowboy shot, sunset, backlighting, holding bug net, straw hat, white t-shirt, green shorts, short hair, brown hair',
    'male child, 1boy, solo, upper body, laughing, closed eyes, messy hair, light brown hair, blue and white striped shirt',
  ],
  nohuman: [
    'no humans, scenery, mountains, lake, reflection, clouds, sky',
    'no humans, scenery, city, skyscrapers, night, lights',
    'no humans, scenery, forest, river, rocks, moss',
    'no humans, scenery, ocean, waves, lighthouse, cliff',
    'no humans, indoors, bedroom, bed, window, plants, desk',
    'no humans, still life, fruit, basket, table, cloth',
    'no humans, cat, sitting, windowsill, curtains',
    'no humans, dog, running, grass, outdoors',
    'no humans, scenery, japanese street, power lines, vending machine',
    'no humans, scenery, snow, village, houses, winter',
    'no humans, food, ramen, bowl, chopsticks, steam',
    'no humans, flower, bouquet, vase, white background',
    'no humans, scenery, castle, fantasy, waterfall, floating island',
    'no humans, bird, branch, cherry blossoms, spring',
    'no humans, scenery, train, railroad, countryside, field',
  ],
}

export const DATASET_PROMPTS: readonly DatasetPrompt[] = DATASET_CATEGORIES.flatMap(category =>
  (PROMPTS[category.id] ?? []).map((prompt, index) => ({ id: `${category.id}-${index + 1}`, category: category.id, prompt })))
