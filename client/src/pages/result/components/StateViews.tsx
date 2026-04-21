import { View, Text } from '@tarojs/components'
import NavBar from '../../../components/NavBar'
import { LoadingIllustration, ErrorIllustration, EmptyIllustration } from '../../../components/ResultIllustrations'
import ActiveLoading from '../../../components/ActiveLoading'
import { PAGE_STATE_MESSAGES } from '../utils'
import type { ResultPageState } from '../../../types/view/render-scene.vm'

interface Props {
  pageState: ResultPageState
  errorCode: string | null
  errorMsg: string | null
  navBarHeight: number
  onRetry: () => void
}

export default function StateViews({ pageState, errorCode, errorMsg, navBarHeight, onRetry }: Props) {
  const shell = (content: React.ReactNode) => (
    <View className='result-page'>
      <NavBar title='Claread透读' showBack showHome />
      <View style={{ height: navBarHeight + 'px', flexShrink: 0 }} />
      {content}
    </View>
  )

  if (pageState === 'loading') {
    return shell(
      <View className='state-container'>
        <ActiveLoading />
      </View>
    )
  }

  if (pageState === 'empty') {
    const msg = PAGE_STATE_MESSAGES.empty!
    return shell(
      <View className='state-container'>
        <View className='state-vertical'>
          <EmptyIllustration />
          <Text className='state-title'>{msg.title}</Text>
          <Text className='state-subtitle'>{msg.subtitle}</Text>
        </View>
        <View className='state-cta safe-area-bottom'>
          <View className='btn-primary' onClick={onRetry}>
            <Text className='btn-primary-text'>修改重试</Text>
          </View>
        </View>
      </View>
    )
  }

  if (pageState === 'failed' || pageState === 'timeout' || pageState === 'network_fail') {
    const defaultMsg = PAGE_STATE_MESSAGES[pageState]!
    const title = errorCode === 'INSUFFICIENT_CREDITS' ? '今日积分不足' : defaultMsg.title
    const subtitle = errorCode === 'INSUFFICIENT_CREDITS' ? errorMsg || '您的积分已耗尽，请明天再试' : defaultMsg.subtitle

    return shell(
      <View className='state-container'>
        <View className='state-vertical'>
          <ErrorIllustration />
          <Text className='state-title'>{title}</Text>
          <Text className='state-subtitle'>{subtitle}</Text>
        </View>
        <View className='state-cta safe-area-bottom'>
          <View className='btn-primary' onClick={onRetry}>
            <Text className='btn-primary-text'>重新分析</Text>
          </View>
        </View>
      </View>
    )
  }

  return shell(
    <View className='state-container'>
      <View className='state-vertical'>
        <LoadingIllustration />
        <Text className='state-title'>正在解析文章...</Text>
        <Text className='state-subtitle-secondary'>首次解析可能需要 20-40 秒，请耐心等待</Text>
      </View>
    </View>
  )
}
