/**
 * 环境配置
 *
 * local:  本机后端，单人联调
 * dev:    共享开发环境，真机多人联调
 * prod:   正式环境
 */

export type Env = 'local' | 'dev' | 'staging' | 'prod'

export interface EnvConfig {
  env: Env
  apiBaseUrl: string
}

// 使用编译时注入的环境变量（TARO_APP_ENV 通过 defineConstants 注入）
// 小程序环境无 process 对象，只能用编译时常量
declare const TARO_APP_ENV: string | undefined
const env: Env = (TARO_APP_ENV as Env) || 'local'

const envConfigs: Record<Env, EnvConfig> = {
  local: {
    env: 'local',
    apiBaseUrl: 'http://192.168.1.222:8000',
  },
  dev: {
    env: 'dev',
    apiBaseUrl: 'http://192.168.1.222:8000',
  },
  staging: {
    env: 'staging',
    apiBaseUrl: 'https://staging-api.claread.com',
  },
  prod: {
    env: 'prod',
    apiBaseUrl: 'https://api.claread.com',
  },
}

export const envConfig: EnvConfig = envConfigs[env]
