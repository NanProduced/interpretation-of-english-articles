const ROUTES = {
  HOME: '/pages/home/index',
  INPUT: '/pages/input/index',
  RESULT: '/pages/result/index',
  HISTORY: '/pages/history/index',
  VOCAB: '/pages/vocab/index',
  PROFILE: '/pages/profile/index',
  FEEDBACK: '/pages/feedback/index',
  FEEDBACK_MY: '/pages/feedback/my-feedback',
  CREDIT_DETAIL: '/pages/credit-detail/index',
  DAILY_READER: '/pages/daily-reader/index',
  DAILY_READER_ARCHIVE: '/pages/daily-reader-archive/index',
  ONBOARDING: '/pages/onboarding/index',
} as const

type RouteKey = keyof typeof ROUTES
type RoutePath = (typeof ROUTES)[RouteKey]

export { ROUTES }
export type { RouteKey, RoutePath }
