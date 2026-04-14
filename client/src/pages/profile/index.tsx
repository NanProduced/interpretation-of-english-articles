/**
 * 个人中心页
 *
 * 展示用户信息、登录/登出入口，
 * 以及学习统计和设置入口。
 */

import { View, Text, ScrollView, Image, Button, Input } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useState, useEffect, useCallback, useRef } from 'react'
import { useConfigStore } from '../../stores/config'
import { useAuthStore } from '../../stores/auth'
import { ensureLoggedIn } from '../../services/auth'
import { getAllRecords, getVocabulary } from '../../services/storage'
import { fetchCloudRecords } from '../../services/api/records.client'
import { fetchCloudVocabulary } from '../../services/api/vocabulary.client'
import { fetchUserQuota, updateProfile } from '../../services/api/client'
import NavBar from '../../components/NavBar'
import TabBar from '../../components/TabBar'
import LucideIcon from '../../components/LucideIcon'
import { useLayoutStore } from '../../stores/layout'
import { getDisplayLabel, ReadingGoal } from '../../config/purpose'
import './index.scss'

interface ProfilePageProps {
  isSubView?: boolean
}

export default function ProfilePage({ isSubView = false }: ProfilePageProps) {
  const { purpose, level } = useConfigStore()
  const { navBarHeight } = useLayoutStore()
  const { isLoggedIn, userInfo, logout, fetchUserInfo, updateUserInfo } = useAuthStore()
  const [articleCount, setArticleCount] = useState(0)
  const [wordCount, setWordCount] = useState(0)
  const [quota, setQuota] = useState<{ remaining: number, dailyFree: number, bonus: number } | null>(null)
  const [loadingStats, setLoadingStats] = useState(false)
  
  // 获取阅读等级头衔与勋章进化
  const getReadingTier = (count: number) => {
    if (count === 0) return { title: '初探者', icon: 'award', color: '#a1a1aa' }
    if (count < 5) return { title: '求知者', icon: 'bookOpen', color: 'var(--color-ink)' }
    if (count < 20) return { title: '博学者', icon: 'medal', color: '#B8860B' } // 深金
    return { title: '硕儒', icon: 'crown', color: 'var(--color-exam)' } // 绯红
  }
  
  const tier = getReadingTier(articleCount)
  // 昵称更新防抖定时器
  const nicknameTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  /**
   * 加载统计数据。
   * - 已登录：优先从云端读取（articleCount = 云端记录数，wordCount = 云端生词本数）
   * - 未登录：从本地读取
   */
  const loadStats = useCallback(async () => {
    setLoadingStats(true)
    if (isLoggedIn) {
      try {
        const [recordResult, vocabResult, quotaResult] = await Promise.all([
          fetchCloudRecords(1, 1).catch(() => ({ total: 0 })),
          fetchCloudVocabulary(1, 1).catch(() => ({ total: 0 })),
          fetchUserQuota().catch(() => null),
        ])
        setArticleCount(recordResult.total)
        setWordCount(vocabResult.total)
        if (quotaResult) {
          setQuota({ 
            remaining: quotaResult.remaining_points, 
            dailyFree: quotaResult.daily_free_points,
            bonus: quotaResult.bonus_points || 0
          })
        }
      } catch {
        // 云端读取失败，降级到本地
        const records = getAllRecords()
        setArticleCount(records.length)
        const vocab = getVocabulary()
        setWordCount(vocab.length)
      }
    } else {
      const records = getAllRecords()
      setArticleCount(records.length)
      const vocab = getVocabulary()
      setWordCount(vocab.length)
      setQuota(null)
    }
    setLoadingStats(false)
  }, [isLoggedIn])

  // 启动时加载 + isLoggedIn 变化时重新加载
  useEffect(() => {
    loadStats()
    if (isLoggedIn) {
      fetchUserInfo()
    }
  }, [isLoggedIn, loadStats])

  const handleLogin = async () => {
    // 立即设置标志，防止 app.tsx restore 和 handleLogin 重复触发跳转
    ;(Taro as any)._navigatingToOnboarding = true
    const result = await ensureLoggedIn()
    if (result.success) {
      // 首次登录（未设置过用户配置），跳转 onboarding
      if (result.isFirstLogin) {
        Taro.navigateTo({ url: '/pages/onboarding/index' })
      }
      // ensureLoggedIn 成功后 auth store 已更新，useEffect 会自动触发 loadStats
    }
  }

  const handleLogout = () => {
    Taro.showModal({
      title: '确认退出登录？',
      content: '退出后，您的阅读进度和生词本将保留在本地，云端同步暂停。',
      confirmText: '退出登录',
      confirmColor: '#ef4444',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          logout()
          // 登出后，useEffect 会检测到 isLoggedIn=false，自动切换到本地统计
        }
      }
    })
  }

  const onChooseAvatar = (e: any) => {
    const { avatarUrl } = e.detail
    updateUserInfo({ avatar_url: avatarUrl })
    updateProfile({ avatar_url: avatarUrl }).catch(() => {
      Taro.showToast({ title: '头像保存失败', icon: 'error' })
    })
  }

  const onNicknameChange = (e: any) => {
    const nickname = e.detail.value
    updateUserInfo({ nickname })
    // 防抖：300ms 内只发送最后一次
    if (nicknameTimerRef.current !== null) {
      clearTimeout(nicknameTimerRef.current)
    }
    nicknameTimerRef.current = setTimeout(() => {
      updateProfile({ nickname }).catch(() => {
        Taro.showToast({ title: '昵称保存失败', icon: 'error' })
      })
    }, 300)
  }

  const menuGroups = [
    {
      title: "学习管理",
      items: [
        {
          label: "当前模式配置",
          value: getDisplayLabel(purpose as ReadingGoal, level),
          icon: 'settings',
          url: '/pages/onboarding/index?from=profile',
          color: 'blue',
        },
        {
          label: "我的生词本",
          value: wordCount > 0 ? `${wordCount}词` : "暂无生词",
          icon: 'bookmark',
          url: '/pages/vocab/index',
          color: 'yellow',
        },
      ]
    },
    {
      title: "关于与合规",
      items: [
        { label: "用户协议与隐私政策", icon: 'file', color: 'gray' },
        { label: "关于我们", icon: 'info', color: 'gray' },
      ]
    }
  ]

  const handleMenuClick = (item: { url?: string }) => {
    if (item.url) {
      Taro.navigateTo({ url: item.url })
    }
    // 无 url 的项仅为展示，不触发导航
  }

  const displayName = userInfo?.nickname || (isLoggedIn ? `用户 ${(userInfo?.user_id || '').slice(0, 8)}` : '未登录')
  const avatarChar = isLoggedIn ? 'U' : 'M'

  return (
    <View className={`profile-page ${isSubView ? 'sub-view' : ''}`}>
      {!isSubView && <NavBar title='我的' />}
      {!isSubView && <View style={{ height: navBarHeight + 'px', flexShrink: 0 }} />}
      <ScrollView scrollY className='profile-scroll'>

        {/* User Card */}
        <View className='user-card'>
          <View className='user-profile-section'>
            <Button
              className='avatar-btn'
              openType={isLoggedIn ? 'chooseAvatar' : undefined}
              onChooseAvatar={isLoggedIn ? onChooseAvatar : undefined}
              onClick={!isLoggedIn ? handleLogin : undefined}
              aria-label={isLoggedIn ? '修改头像' : '点击登录'}
            >
              {userInfo?.avatar_url ? (
                <Image className='avatar-img' src={userInfo.avatar_url} mode='aspectFill' />
              ) : (
                <LucideIcon name='user' size={32} color={isLoggedIn ? '#fff' : 'var(--text-muted)'} />
              )}
            </Button>

            <View className='user-info'>
              {isLoggedIn ? (
                <View className='nickname-wrapper'>
                  <Input
                    className='nickname-input'
                    type='nickname'
                    value={userInfo?.nickname || ''}
                    placeholder='点击设置昵称'
                    placeholderStyle='color: #a1a1aa; font-weight: 500;'
                    maxlength={20}
                    onBlur={onNicknameChange}
                    onConfirm={onNicknameChange}
                  />
                  <View className='edit-icon-box' aria-label='修改昵称'>
                    <LucideIcon name='pencil' size={14} color='currentColor' />
                  </View>
                </View>
              ) : (
                <View className='nickname-wrapper' onClick={handleLogin}>
                  <Text className='nickname'>点击登录微信</Text>
                  <Text className='login-subtitle'>登录后可同步数据到云端</Text>
                </View>
              )}
            </View>

            {isLoggedIn && (
              <View 
                className='logout-icon-btn' 
                onClick={handleLogout}
                aria-label='退出登录'
              >
                <LucideIcon name='logOut' size={20} color='var(--text-muted)' />
              </View>
            )}
          </View>

          {/* Account Metrics Portfolio */}
          <View className='stats-dashboard'>
            <View className='dashboard-header'>
              <View className='badge-row'>
                <Text className='badge'>标准学者</Text>
              </View>
              <View className='total-preview'>
                <Text className='label'>当前可用</Text>
                <Text className={`value ${loadingStats ? 'is-loading' : ''}`}>
                  {loadingStats ? '同步中' : ((quota?.remaining ?? 0) + (quota?.bonus ?? 0))}
                </Text>
              </View>
            </View>

            <View className='credits-list'>
              <View className='credit-item'>
                <View className='item-info'>
                  <LucideIcon name='calendar' size={14} color='var(--text-muted)' />
                  <View className='text-group'>
                    <Text className='title'>每日常规额度</Text>
                    <Text className='subtitle'>每日 00:00 自动刷新</Text>
                  </View>
                </View>
                <Text className='count'>{loadingStats ? '...' : (quota?.remaining ?? 0)}</Text>
              </View>

              <View className='credit-divider' />

              <View className='credit-item'>
                <View className='item-info'>
                  <LucideIcon name='sparkles' size={14} color='var(--text-muted)' />
                  <View className='text-group'>
                    <Text className='title'>永久奖励积分</Text>
                    <Text className='subtitle'>通过活动或分享获得</Text>
                  </View>
                </View>
                <Text className='count'>{loadingStats ? '...' : (quota?.bonus ?? 0)}</Text>
              </View>
            </View>

            {/* Achievement Coronation */}
            <View className='dashboard-footer'>
              <View className='achievement-badge'>
                <View className='medal-icon' style={{ borderColor: tier.color + '20' }}>
                  <LucideIcon name={tier.icon as any} size={16} color={tier.color} />
                </View>
                <View className='text-group'>
                  <Text className='history-label'>已读存档</Text>
                  <Text className='tier-text' style={{ color: tier.color }}>{tier.title}</Text>
                </View>
              </View>
              <View className='history-value-box'>
                <Text className='history-value' style={{ color: articleCount > 0 ? tier.color : 'var(--color-ink)' }}>
                  {loadingStats ? '...' : articleCount}
                </Text>
              </View>
            </View>
          </View>
        </View>

        <View className='menu-list'>
          {menuGroups.map((group, gIdx) => (
            <View key={gIdx} className='menu-group'>
              <Text className='group-title'>{group.title}</Text>
              <View className='group-box'>
                {group.items.map((item, iIdx) => (
                  <View key={iIdx} className='menu-item' onClick={() => handleMenuClick(item)}>
                    <View className='item-left'>
                      <View className={`icon-box ${item.color}`}>
                        <LucideIcon name={item.icon as any} size={18} color='currentColor' />
                      </View>
                      <Text className='label'>{item.label}</Text>
                    </View>
                    <View className='item-right'>
                      {item.value && <Text className='value-tag'>{item.value}</Text>}
                      {item.url && <LucideIcon name='chevronRight' size={16} color='#ccc' />}
                    </View>
                  </View>
                ))}
              </View>
            </View>
          ))}

        </View>

        <View className='version-tag'>
          <Text>AI Reader v1.0.0</Text>
        </View>
        <View style={{ height: '160rpx' }} />
      </ScrollView>

      {!isSubView && <TabBar current='profile' />}
    </View>
  )
}
