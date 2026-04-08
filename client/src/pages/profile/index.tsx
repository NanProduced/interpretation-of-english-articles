/**
 * 个人中心页
 *
 * 展示用户信息、登录/登出入口，
 * 以及学习统计和设置入口。
 */

import { View, Text, ScrollView, Image, Button, Input } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useState, useEffect, useCallback } from 'react'
import { useConfigStore } from '../../stores/config'
import { useAuthStore } from '../../stores/auth'
import { ensureLoggedIn } from '../../services/auth'
import { getAllRecords, getVocabulary } from '../../services/storage'
import { fetchCloudRecords } from '../../services/api/records.client'
import { fetchCloudVocabulary } from '../../services/api/vocabulary.client'
import NavBar from '../../components/NavBar'
import TabBar from '../../components/TabBar'
import LucideIcon from '../../components/LucideIcon'
import { useLayoutStore } from '../../stores/layout'
import './index.scss'

interface ProfilePageProps {
  isSubView?: boolean
}

export default function ProfilePage({ isSubView = false }: ProfilePageProps) {
  const { purpose } = useConfigStore()
  const { navBarHeight } = useLayoutStore()
  const { isLoggedIn, userInfo, logout, fetchUserInfo, updateUserInfo } = useAuthStore()
  const [articleCount, setArticleCount] = useState(0)
  const [wordCount, setWordCount] = useState(0)
  const [loadingStats, setLoadingStats] = useState(false)

  /**
   * 加载统计数据。
   * - 已登录：优先从云端读取（articleCount = 云端记录数，wordCount = 云端生词本数）
   * - 未登录：从本地读取
   */
  const loadStats = useCallback(async () => {
    setLoadingStats(true)
    if (isLoggedIn) {
      try {
        const [recordResult, vocabResult] = await Promise.all([
          fetchCloudRecords(1, 1),
          fetchCloudVocabulary(1, 1),
        ])
        setArticleCount(recordResult.total)
        setWordCount(vocabResult.total)
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
    const success = await ensureLoggedIn()
    if (success) {
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
  }

  const onNicknameChange = (e: any) => {
    const nickname = e.detail.value
    updateUserInfo({ nickname })
  }

  const purposeMap: Record<string, string> = {
    'daily': '日常阅读',
    'exam': 'CET-4 备考',
    'academic': '学术/专业'
  }

  const menuGroups = [
    {
      title: "学习管理",
      items: [
        { label: "当前模式配置", value: purposeMap[purpose] || "未设置", icon: 'settings', url: '/pages/onboarding/index', color: 'blue' },
        { label: "我的生词本", value: wordCount > 0 ? `${wordCount}词` : "暂无生词", icon: 'bookmark', color: 'yellow' },
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
          <Button
            className='avatar-btn'
            openType={isLoggedIn ? 'chooseAvatar' : undefined}
            onChooseAvatar={isLoggedIn ? onChooseAvatar : undefined}
            onClick={!isLoggedIn ? handleLogin : undefined}
          >
            {userInfo?.avatar_url ? (
              <Image className='avatar-img' src={userInfo.avatar_url} mode='aspectFill' />
            ) : (
              <View className='avatar-text'>{avatarChar}</View>
            )}
          </Button>

          <View className='user-info'>
            {isLoggedIn ? (
              <Input
                className='nickname-input'
                type='nickname'
                value={userInfo?.nickname || ''}
                placeholder='设置昵称'
                maxlength={20}
                onBlur={onNicknameChange}
                onConfirm={onNicknameChange}
              />
            ) : (
              <Text className='nickname' onClick={handleLogin}>点击登录微信</Text>
            )}
            <View className='stats-row'>
              {loadingStats ? (
                <Text className='stats-label'>加载中...</Text>
              ) : articleCount > 0 ? (
                <>
                  <Text className='stats-label'>已读 </Text>
                  <Text className='stats-value'>{articleCount}</Text>
                  <Text className='stats-label'> 篇文章</Text>
                </>
              ) : (
                <Text className='stats-label'>暂无阅读记录</Text>
              )}
            </View>
          </View>

          {isLoggedIn && (
            <View className='logout-icon-btn' onClick={handleLogout}>
              <LucideIcon name='logOut' size={20} color='var(--text-muted)' />
            </View>
          )}
        </View>

        <View className='login-tip'>
          <Text className='tip-text'>
            {isLoggedIn ? '已登录 · 数据已同步到云端' : '登录后可同步数据到云端，跨设备查看'}
          </Text>
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
                      <LucideIcon name='chevronRight' size={16} color='#ccc' />
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
