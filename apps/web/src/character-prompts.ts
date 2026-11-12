/**
 * Content-only character libraries, independently edited for GPT and Precise.
 * Every item owns its framing and pose; categories are not combined at runtime.
 * Identity, clothing and accessories come from traits, and style comes from the pool.
 */
import type { DatasetCategory, DatasetPrompt } from './dataset-run'

export type CharacterMode = 'gpt' | 'precise'

export interface CharacterCategory extends DatasetCategory {
  defaultSelected: boolean
}

interface LibraryCategory {
  id: string
  label: string
  description: string
  prompts: readonly string[]
}

function library(mode: CharacterMode, source: readonly LibraryCategory[]) {
  const categories: readonly CharacterCategory[] = source.map(category => ({
    id: `char-${mode}-${category.id}`, label: category.label,
    description: category.description, defaultSelected: true,
  }))
  const prompts: readonly DatasetPrompt[] = source.flatMap(category => category.prompts.map((prompt, index) => ({
    id: `char-${mode}-${category.id}-${index + 1}`,
    category: `char-${mode}-${category.id}`,
    // Explicit whole-body framing matters for folded or heavily foreshortened poses.
    prompt: prompt.split(', ').includes('full body') ? `${prompt}, hands and feet in frame` : prompt,
  })))
  return { categories, prompts }
}

const GPT_LIBRARY = library('gpt', [
  {
    id: 'face', label: '肖像与五官', description: '正面、侧面、回头与俯仰视角，清楚展示五官和头部朝向',
    prompts: [
      'portrait, front view, head upright, expressionless, looking at viewer, simple background',
      'close-up, face focus, three-quarter view, light smile, looking at viewer',
      'portrait, from side, profile, head upright, closed mouth, looking ahead',
      'close-up, face focus, from above, looking up, curious',
      'portrait, from behind, looking back, head turned, calm, simple background',
      'close-up, face focus, front view, head tilt, gentle smile',
      'portrait, from below, head upright, looking down, serious',
      'close-up, face focus, from side, profile, half-closed eyes',
      'portrait, three-quarter view, head turned, looking away, expressionless',
      'close-up, face focus, from below, looking down, light smile',
      'portrait, from above, head tilt, looking at viewer, laughing, closed eyes',
      'close-up, face focus, three-quarter view, head upright, serious',
    ],
  },
  {
    id: 'standing', label: '站姿与正侧背', description: '自然站姿、重心变化与手臂位置，混合正侧背和俯仰视角',
    prompts: [
      'full body, front view, standing, arms at sides, feet together, simple background',
      'full body, from side, profile, standing, hands behind back, looking ahead',
      'full body, from behind, standing, arms at sides, feet apart, simple background',
      'full body, three-quarter view, standing, hand on own hip, weight on one leg',
      'full body, from above, standing, hands together, looking up',
      'full body, from below, three-quarter view, standing, arms crossed, looking ahead',
      'full body, from side, standing, looking back, one hand raised, light smile',
      'full body, front view, standing, one knee bent, arms at sides, relaxed',
      'full body, from behind, three-quarter view, standing, hands on own hips',
      'full body, from below, front view, standing, waving, light smile',
      'full body, three-quarter view, standing, one foot forward, hands behind back',
      'full body, from above, from side, standing, arms crossed, looking down',
      'full body, front view, standing, palms open, elbows bent, smile',
      'full body, from behind, standing, looking back, hand on own chest',
    ],
  },
  {
    id: 'upper', label: '半身与手部动作', description: '半身构图下的自然手势和上身转向，避免每张都正面垂手',
    prompts: [
      'upper body, three-quarter view, standing, hand on own chest, gentle smile',
      'upper body, front view, standing, waving, looking at viewer',
      'upper body, from side, profile, standing, arms crossed, serious',
      'upper body, from above, sitting, hand on own chin, looking up',
      'cowboy shot, from behind, standing, looking back, hands behind back',
      'upper body, from below, three-quarter view, standing, hands together, calm',
      'upper body, front view, sitting, hand on own cheek, head tilt, light smile',
      'cowboy shot, from side, standing, one hand raised, looking ahead',
      'upper body, three-quarter view, sitting, resting elbows on table, hands together',
      'upper body, from behind, sitting, looking to the side, arms at sides',
      'upper body, from above, standing, peace sign, smile, looking at viewer',
      'cowboy shot, from below, front view, standing, hands on own hips, confident',
    ],
  },
  {
    id: 'sitting', label: '坐姿与休息', description: '椅上、地面和跪坐，变化腿部位置、躯干朝向和观察角度',
    prompts: [
      'full body, from side, sitting, on chair, feet on floor, hands on own knees',
      'full body, front view, sitting, on chair, crossed legs, hands together',
      'full body, three-quarter view, sitting, on floor, legs to one side, relaxed',
      'full body, from behind, sitting, on bench, hands beside hips, looking ahead',
      'full body, from above, sitting, on floor, crossed legs, hands on own knees',
      'full body, from below, from side, sitting, on chair, arms crossed, looking ahead',
      'full body, front view, seiza, hands on own thighs, calm, simple background',
      'full body, from side, sitting, on floor, knees together, hugging own knees',
      'full body, from behind, three-quarter view, sitting, on chair, looking back',
      'full body, three-quarter view, sitting, on ground, legs extended, hands beside hips',
      'full body, from above, sitting, on chair, ankles crossed, hands on own lap',
      'full body, from side, seiza, back straight, hands on own knees',
      'full body, front view, sitting, on bench, feet apart, leaning forward, elbows on knees',
      'full body, from below, three-quarter view, sitting, on floor, knees bent, leaning back',
    ],
  },
  {
    id: 'daily', label: '普通动作与日常场景', description: '迈步、转身、轻蹲与伸手；每个场景都明确安排动作和视角',
    prompts: [
      'full body, three-quarter view, walking, one foot forward, arms swinging, park',
      'full body, from behind, walking away, arms at sides, path',
      'full body, from side, walking, looking ahead, arms swinging, street',
      'cowboy shot, front view, turning around, looking to the side, one hand raised',
      'full body, from above, kneeling, hands on own knees, looking up',
      'full body, from below, three-quarter view, standing, stretching, arms up',
      'full body, from side, squatting, heels on ground, hands on own knees',
      'upper body, three-quarter view, sitting, leaning forward, hand on own chin, library',
      'full body, from behind, three-quarter view, standing, leaning against wall, arms crossed',
      'upper body, from above, standing, reaching, outstretched hand, looking at hand',
      'full body, front view, walking, looking to the side, hand on own chest, courtyard',
      'full body, from below, from side, standing, looking ahead, hands behind back, window light',
    ],
  },
])

const PRECISE_LIBRARY = library('precise', [
  {
    id: 'identity', label: '基础身份与普通动作', description: '特写、普通站坐和正侧背，衔接复杂动作，保持角色辨识度',
    prompts: [
      'portrait, front view, head upright, light smile, looking at viewer, simple background',
      'full body, from side, profile, standing, arms at sides, feet together',
      'close-up, face focus, three-quarter view, looking at viewer, expressionless',
      'full body, from behind, standing, hands behind back, looking ahead',
      'portrait, from above, head tilt, looking up, curious',
      'full body, three-quarter view, sitting, on chair, feet on floor, hands on own knees',
      'full body, front view, standing, arms crossed, weight on one leg',
      'close-up, face focus, from below, looking down, serious',
      'full body, from behind, three-quarter view, sitting, on floor, legs to one side',
      'upper body, from side, standing, hand on own chest, looking ahead',
      'full body, from above, standing, hands on own hips, looking up',
      'full body, from below, three-quarter view, walking, one foot forward, arms swinging',
    ],
  },
  {
    id: 'balance', label: '重心与平衡', description: '单腿、弓步、侧倾和深蹲，明确承重腿、躯干方向与手臂位置',
    prompts: [
      'full body, from side, standing on one leg, raised knee, arms out, balancing',
      'full body, front view, standing on one leg, leg extended to side, arms out',
      'full body, from behind, three-quarter view, standing on one leg, leaning forward, arms out',
      'full body, from above, lunging, front knee bent, back leg extended, hands on own hips',
      'full body, three-quarter view, squatting, feet apart, arms forward, back straight',
      'full body, from below, from side, standing on one leg, leg extended forward, hands together',
      'full body, front view, side lunge, one knee bent, other leg extended, hands on own knees',
      'full body, from behind, standing on one leg, arms up, back straight',
      'full body, from side, tiptoes, arms out, back straight, balancing',
      'full body, three-quarter view, kneeling, on one knee, arms spread, torso turned',
      'full body, from above, from side, squatting, heels on ground, hands together',
      'full body, from below, front view, feet apart, leaning to side, one arm overhead',
      'full body, from behind, side lunge, arms out, looking to the side',
      'full body, three-quarter view, standing on one leg, raised knee, elbows bent, palms open',
    ],
  },
  {
    id: 'yoga', label: '瑜伽与拉伸', description: '树式、战士式、三角伸展、下犬式等，以肢体关系描述动作并混合视角',
    prompts: [
      'full body, front view, yoga, standing on one leg, sole against inner calf, hands together',
      'full body, from side, yoga, lunging, front knee bent, back leg extended, arms up',
      'full body, three-quarter view, yoga, feet apart, arms out, front knee bent, looking to the side',
      'full body, from behind, yoga, standing on one leg, sole against inner calf, arms up',
      'full body, from above, yoga, triangle pose, legs straight, one hand near ankle, other arm up',
      'full body, from side, yoga, downward dog, palms on floor, hips raised, legs straight',
      'full body, from below, three-quarter view, yoga, lunging, back knee on floor, arms up',
      'full body, front view, yoga, sitting, crossed legs, back straight, palms on knees',
      'full body, from behind, three-quarter view, yoga, seated twist, one knee bent, torso turned',
      'full body, from side, yoga, lying, on stomach, palms beneath shoulders, chest raised',
      'full body, from above, yoga, lying, on back, knees bent, feet on floor, hips raised',
      'full body, three-quarter view, yoga, kneeling, sitting on heels, arms overhead, back straight',
      'full body, from behind, yoga, downward dog, palms on floor, hips raised, legs straight',
      'full body, from side, yoga, side plank, supported on one hand, legs extended, other arm up',
      'full body, from above, three-quarter view, yoga, child pose, kneeling, torso folded forward, arms extended',
      'full body, front view, yoga, kneeling, one leg extended to side, leaning to side, one arm overhead',
    ],
  },
  {
    id: 'fold', label: '前屈与碰脚尖', description: '坐位体前屈、站立前屈和单腿伸展，区分手部目标、腿部位置和俯仰视角',
    prompts: [
      'full body, from side, sitting, seated forward fold, legs extended, feet together, hands reaching for toes',
      'full body, three-quarter view, sitting, legs extended, leaning forward, fingertips near toes',
      'full body, from above, sitting, seated forward fold, legs extended, hands holding ankles',
      'full body, from behind, three-quarter view, sitting, legs extended, torso folded forward, arms extended',
      'full body, front view, sitting, legs apart, leaning forward, palms on floor',
      'full body, from side, standing, bent over, legs straight, hands reaching for toes',
      'full body, from above, three-quarter view, standing, bent over, feet together, fingertips near toes',
      'full body, from behind, standing, bent over, feet apart, palms near ankles',
      'full body, from below, from side, standing, one knee bent, other leg extended, hands reaching for toes',
      'full body, three-quarter view, sitting, one leg extended, other knee bent, hands reaching for toes',
      'full body, from above, sitting, one leg extended, torso turned, hand holding ankle',
      'full body, from side, kneeling, one leg extended forward, leaning forward, fingertips near toes',
      'full body, front view, standing, feet apart, bent over, one hand reaching opposite foot, other arm up',
      'full body, from behind, three-quarter view, sitting, legs apart, torso folded forward, hands reaching forward',
    ],
  },
  {
    id: 'ground', label: '四肢支撑与地面动作', description: '四肢着地、爬行、平板支撑、跪伏与卧姿，保持手脚支点可见',
    prompts: [
      'full body, from side, all fours, palms under shoulders, knees under hips, back straight',
      'full body, three-quarter view, all fours, one hand reaching forward, knees on floor',
      'full body, from above, all fours, palms on floor, looking ahead, neutral spine',
      'full body, from behind, three-quarter view, all fours, head turned to side, back straight',
      'full body, front view, all fours, one hand raised, balanced on three limbs',
      'full body, from side, crawling, opposite hand and knee forward, looking ahead',
      'full body, from below, three-quarter view, plank, palms under shoulders, legs extended, back straight',
      'full body, from above, from side, kneeling, hands on floor, one leg extended backward',
      'full body, three-quarter view, sitting, knees bent, palms behind hips, hips raised',
      'full body, from behind, from above, crawling, opposite hand and knee forward',
      'full body, from side, lying, on back, one knee raised, arms out',
      'full body, front view, lying, on side, supported on elbow, knees bent',
      'full body, from above, lying, on stomach, head raised, elbows on floor',
      'full body, three-quarter view, kneeling, on one knee, one hand on floor, torso turned',
    ],
  },
  {
    id: 'combat', label: '战斗与运动动作', description: '徒手格斗、闪避、踢腿、起跑、腾空与落地，混合方向和透视',
    prompts: [
      'full body, three-quarter view, fighting stance, feet apart, knees bent, fists raised, serious',
      'full body, from side, punching, one fist extended, other fist near chest, torso turned',
      'full body, front view, kicking, leg extended forward, arms guarding face, focused',
      'full body, from behind, three-quarter view, fighting stance, one foot forward, fists raised',
      'full body, from above, dodging, lunging to side, torso lowered, arms bent',
      'full body, from below, from side, high kick, one leg raised, arms out, balancing',
      'full body, three-quarter view, crouching, one knee near ground, hands raised, looking ahead',
      'full body, from behind, punching, torso turned, front knee bent',
      'full body, front view, fighting stance, blocking, crossed forearms, knees bent',
      'full body, from side, running, leaning forward, arms pumping, one knee raised',
      'full body, from above, three-quarter view, starting sprint, one hand on ground, front knee bent',
      'full body, from below, jumping, knees bent, arms spread, focused',
      'full body, from behind, three-quarter view, running, arms pumping, looking ahead',
      'full body, from side, landing, one knee bent, one hand reaching toward ground',
      'full body, from above, fighting stance, pivoting, torso turned, fists raised',
      'full body, three-quarter view, spinning kick, leg extended to side, arms guarding face',
    ],
  },
])

/** New pickers use only their mode's library; existing runs keep frozen item text. */
export function characterCategories(mode: CharacterMode): readonly CharacterCategory[] {
  return (mode === 'gpt' ? GPT_LIBRARY : PRECISE_LIBRARY).categories
}

export function characterPrompts(mode: CharacterMode): readonly DatasetPrompt[] {
  return (mode === 'gpt' ? GPT_LIBRARY : PRECISE_LIBRARY).prompts
}

/** Saved review category labels include older shared-library item IDs. */
export const CHARACTER_CATEGORIES: readonly CharacterCategory[] = [
  { id: 'char-framing', label: '景别与角度', description: '', defaultSelected: false },
  { id: 'char-face', label: '脸部特写', description: '', defaultSelected: false },
  { id: 'char-angle', label: '侧面与背面', description: '', defaultSelected: false },
  { id: 'char-expression', label: '表情', description: '', defaultSelected: false },
  { id: 'char-pose', label: '姿势动作', description: '', defaultSelected: false },
  { id: 'char-setting', label: '场景', description: '', defaultSelected: false },
  { id: 'char-splash', label: '立绘与动态', description: '', defaultSelected: false },
  { id: 'char-light', label: '光照', description: '', defaultSelected: false },
  { id: 'char-outfit', label: '服装变化', description: '', defaultSelected: false },
  ...GPT_LIBRARY.categories,
  ...PRECISE_LIBRARY.categories,
]
