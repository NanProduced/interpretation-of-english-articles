import React, { useState } from 'react'
import { View, Text, ScrollView } from '@tarojs/components'
import Taro from '@tarojs/taro'
import NavBar from '../../components/NavBar'
import LucideIcon from '../../components/LucideIcon'
import { useLayoutStore } from '../../stores/layout'
import './index.scss'

/**
 * 模拟革新版后端数据结构
 */
const notebookData = {
  title: "The Architecture of Sleep",
  paragraphs: [
    {
      id: "p1",
      tag: "Concept",
      sentences: [
        {
          id: "s1",
          chunks: [
            { text: "Sleep is ", type: "main" },
            { text: "the single most effective thing ", type: "main", word: { text: "effective", gloss: "有效的" } },
            { text: "we can do ", type: "clause" },
            { text: "to reset our brain and body health ", type: "modifier", word: { text: "reset", gloss: "重置" } },
            { text: "each day.", type: "modifier" }
          ],
          translation: "睡眠是我们每天能重置身心健康最有效的一件事。"
        },
        {
          id: "s2",
          chunks: [
            { text: "Yet, ", type: "connective" },
            { text: "a silent sleep loss epidemic ", type: "main", word: { text: "epidemic", gloss: "流行病" } },
            { text: "is fast becoming one of the greatest challenges ", type: "main" },
            { text: "in the 21st century.", type: "modifier" }
          ],
          translation: "然而，一场无声的睡眠缺失流行病正成为21世纪最大的挑战。"
        }
      ]
    }
  ]
}

export default function ResultPage() {
  const { navBarHeight } = useLayoutStore()
  const [showTrans, setShowTrans] = useState(true)
  const [showNotes, setShowNotes] = useState(true)
  const [showStructure, setShowStructure] = useState(true)

  const goHome = () => { Taro.reLaunch({ url: '/pages/home/index' }) }
  const goInput = () => { Taro.navigateTo({ url: '/pages/input/index' }) }

  const renderAnnotatedText = (chunks: any[]) => {
    return chunks.map((chunk, idx) => {
      const chunkClass = showStructure ? `chunk-${chunk.type}` : ''
      if (chunk.word && showNotes) {
        return (
          <View key={idx} className={`word-with-note ${chunkClass}`}>
            <Text className='ruby-text'>{chunk.word.gloss}</Text>
            <Text className='surface-text'>{chunk.text}</Text>
          </View>
        )
      }
      return <Text key={idx} className={`text-span ${chunkClass}`}>{chunk.text}</Text>
    })
  }

  return (
    <View className='result-page'>
      <NavBar title='精读笔记' showBack showHome background='#fff' />
      <View className='nav-placeholder' style={{ height: navBarHeight + 'px' }} />

      <ScrollView scrollY className='content-scroll'>
        <View className='article-container'>
          <Text className='article-title'>{notebookData.title}</Text>

          {notebookData.paragraphs.map(para => (
            <View key={para.id} className='paragraph-block'>
              <View className='para-tag'>{para.tag}</View>
              {para.sentences.map((sent, sIdx) => (
                <View key={sent.id} className='sentence-unit' style={{ animationDelay: `${sIdx * 0.2}s` }}>
                  <View className='en-line'>{renderAnnotatedText(sent.chunks)}</View>
                  <View className={`zh-line ${showTrans ? '' : 'hidden'}`}><Text>{sent.translation}</Text></View>
                </View>
              ))}
            </View>
          ))}
        </View>
      </ScrollView>

      {/* 悬浮黑色 Dock 控制栏 - 使用轻量级图标组件 */}
      <View className='minimal-dock'>
        <View className={`dock-item ${showTrans ? 'active' : ''}`} onClick={() => setShowTrans(!showTrans)}>
          <LucideIcon name='languages' size={20} color={showTrans ? '#fbbf24' : '#fff'} />
          <Text className='label'>译文</Text>
        </View>
        <View className={`dock-item ${showNotes ? 'active' : ''}`} onClick={() => setShowNotes(!showNotes)}>
          <LucideIcon name='book' size={20} color={showNotes ? '#fbbf24' : '#fff'} />
          <Text className='label'>批注</Text>
        </View>
        <View className={`dock-item ${showStructure ? 'active' : ''}`} onClick={() => setShowStructure(!showStructure)}>
          <LucideIcon name='layers' size={20} color={showStructure ? '#fbbf24' : '#fff'} />
          <Text className='label'>结构</Text>
        </View>
        
        <View className='divider' />

        <View className='dock-item' onClick={goInput}>
          <LucideIcon name='plus' size={20} color='rgba(255,255,255,0.6)' />
          <Text className='label'>解析</Text>
        </View>
        <View className='dock-item' onClick={goHome}>
          <LucideIcon name='home' size={20} color='rgba(255,255,255,0.6)' />
          <Text className='label'>首页</Text>
        </View>
      </View>
    </View>
  )
}
