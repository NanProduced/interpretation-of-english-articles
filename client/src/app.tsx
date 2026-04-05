import { PropsWithChildren, useEffect } from 'react'
import Taro from '@tarojs/taro'
import './app.scss'

function App({ children }: PropsWithChildren<any>) {
  // 处理小程序切回前台事件
  useEffect(() => {
    const handler = (options: any) => {
      // 场景值参考：https://developers.weixin.qq.com/miniprogram/dev/reference/scene-list.html
      // 1011=长按小程序码  1019=微信打开  1001=聊天顶部  等
      // 暂时：所有切回前台场景统一处理，不区分来源
      // 后续如有需要可按 scene 细化判断逻辑
      console.log('[app] onShow', options.scene, options.path, options.query)
    }

    Taro.onAppShow(handler)
    return () => {
      Taro.offAppShow(handler)
    }
  }, [])

  return children
}

export default App
