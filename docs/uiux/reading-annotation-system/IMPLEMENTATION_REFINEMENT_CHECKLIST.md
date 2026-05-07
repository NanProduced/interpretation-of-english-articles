# Word Lookup System - Precision Refinement Checklist
# 基于 impeccable craft 流程的精细化改进清单
# Date: 2026-05-06
# Scope: WordPopup/index.scss + index.tsx 微调

## 📊 差异分析结果

### ✅ 已完美实现（无需修改）- 20项
见上方对比表

### ⚠️ 需微调的项目（共12项）

#### P0 - 必须修复（影响视觉效果）

1. **[SCSS L232] DictionaryNoteSheet 阴影方向**
   - 当前: `box-shadow: var(--shadow-reader-lg)` → 向下投影
   - 目标: 向上投影 `0 -14rpx 44rpx rgba(17,17,17,.12)`
   - 影响: Sheet看起来像"悬浮卡片"而非"从底部抽出的纸"
   - 修复: 添加专用向上投影变量或在sheet处覆盖

2. **[SCSS L231] Sheet 动画时长**
   - 当前: `animation: slideUp 0.26s` (260ms)
   - 目标: 280ms (`ease-out-expo`)
   - 影响: 动画稍快，不够"从容"
   - 修改为: `animation: slideUp 0.28s var(--ease-out-expo)`

3. **[SCSS L42] Slip 出现动画时长**
   - 当前: `transition: transform 0.16s` (160ms) ✅ 接近但 easing可能不精确
   - 确认: 是否使用了 `var(--ease-reader-out)`? 
   - 如果是 → ✅ OK
   - 如果是默认ease → 改为 `0.16s var(--ease-reader-out)`

4. **[SCSS L344] 来源例句区块圆角**
   - 当前: `border-radius: 20rpx`
   - 目标: 14rpx (更紧凑的嵌套面)
   - 影响: 例句块看起来过于"圆润"，不像轻量嵌套
   - 修改为: `border-radius: 14rpx`

5. **[TSX L459] Sheet Loading 状态**
   - 当前: 使用 `<View className='loading-spinner' />` (spinner)
   - 目标: Skeleton loading (与Slip一致)
   - 影响: 违反"无spinner原则"
   - 修复: 替换为skeleton lines组件

6. **[TSX L250] Slip Empty状态文案**
   - 当前: `'未找到释义'`
   - 目标: `'暂未找到稳定释义'` + 可点击链接
   - 影响: 文案不够友好，缺少降级路径提示
   - 修改文案并添加点击事件

#### P1 - 重要改进（提升品质感）

7. **[SCSS L557] Footer 反馈按钮宽度**
   - 当前: `flex: 0 0 200rpx` (固定200rpx)
   - 问题: 在小屏幕上可能过宽
   - 建议: 改为 `flex: 0 0 auto` + `min-width: 140rpx` + `padding: 0 24rpx`

8. **[SCSS L320-330] 关闭按钮尺寸**
   - 当前: 52rpx × 52rpx
   - 目标规格: 44rpx × 44rpx (更紧凑)
   - 图标尺寸: 当前24px, 可能略大
   - 建议: 调整为 44rpx 容器 + 20px 图标

9. **[SCSS L239-240] Drag Handle 样式**
   - 当前: 54rpx宽 × 5rpx高
   - 建议: 可以稍微加宽至 64rpx 以提高可触摸性
   - 圆角: 已是 pill ✅

10. **[SCSS L428-436] Tab 激活指示器**
    - 当前: 4rpx高的底部border
    - 目标: 更细的线条 (2-3rpx) 或仅颜色变化
    - 建议: 减少到 2rpx，看起来更精致

11. **[SCSS L464] 例句左边框**
    - 当前: `border-left: 2rpx solid var(--reader-border-subtle)`
    - 这是允许的细线（≤1px equivalent in rpx），✅ 可接受
    - 但如果视觉上过重，可改为 1rpx

12. **[TSX L365] Sheet 过渡效果**
    - 当前: `transition: transform 0.26s var(--ease-reader-out)`
    - 拖拽时设置为 `none` ✅ 正确
    - 建议: 确保非拖拽状态使用 `0.28s var(--ease-out-expo)` 与动画一致

## 🎯 实施优先级

### Phase A: 视觉修正（预计30分钟）
- [ ] 修复 #1: Sheet 阴影方向
- [ ] 修复 #2: Sheet 动画时长 260ms → 280ms
- [ ] 修复 #4: 例句圆角 20rpx → 14rpx
- [ ] 修复 #10: Tab indicator 4rpx → 2rpx

### Phase B: 交互优化（预计45分钟）
- [ ] 修复 #5: 替换loading spinner为skeleton
- [ ] 修复 #6: 优化empty state文案
- [ ] 修复 #7: Footer反馈按钮宽度自适应
- [ ] 修复 #8: 关闭按钮尺寸微调

### C. Motion Polish（预计15分钟）
- [ ] 确认 #3: Slip easing函数
- [ ] 修复 #12: Sheet过渡时长统一

## 📝 具体修改代码

### Fix #1: Sheet Shadow (index.scss ~L230-232)

```scss
// BEFORE:
.word-popup-container {
  // ...
  box-shadow: var(--shadow-reader-lg); // 向下投影 ❌
}

// AFTER:
.word-popup-container {
  // ...
  box-shadow: 0 -14rpx 44rpx rgba(17, 17, 17, 0.12); // 向上投影 ✅
}
```

或者更好的做法：在 app.scss 中添加新变量
```scss
// app.scss 新增:
--shadow-reader-sheet: 0 -14rpx 44rpx rgba(17, 17, 17, 0.12);
```
然后在 index.scss 中使用:
```scss
box-shadow: var(--shadow-reader-sheet);
```

### Fix #2: Sheet Animation (index.scss ~L231-237)

```scss
// BEFORE:
@keyframes slideUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

// word-popup-container:
animation: slideUp 0.26s var(--ease-reader-out);

// AFTER:
@keyframes sheetSlideUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

// word-popup-container:
animation: sheetSlideUp 0.28s var(--ease-out-expo);
```

### Fix #4: Source Excerpt Radius (index.scss ~L340-347)

```scss
// BEFORE:
.source-context-excerpt,
.glossary-content {
  // ...
  border-radius: 20rpx; // ❌ 过于圆润
}

// AFTER:
.source-context-excerpt,
.glossary-content {
  // ...
  border-radius: 14rpx; // ✅ 紧凑嵌套面
}
```

### Fix #5: Replace Spinner with Skeleton (index.tsx ~L457-460)

```tsx
// BEFORE:
{loading && !isDisambiguationResult ? (
  <View className='popup-loading-state'>
    <View className='loading-spinner' />
  </View>
) : ...

// AFTER:
{loading && !isDisambiguationResult ? (
  <View className='popup-loading-state'>
    <View className='sheet-skeleton-line' style={{ width: '60%', marginBottom: '16rpx' }} />
    <View className='sheet-skeleton-line' style={{ width: '100%', marginBottom: '16rpx' }} />
    <View className='sheet-skeleton-line' style={{ width: '80%' }} />
  </View>
) : ...
```

并在 SCSS 中添加 (复用 mini 的 skeleton 样式):
```scss
.sheet-skeleton-line {
  height: 28rpx; // 稍高以匹配sheet的行高
  margin-bottom: 16rpx;
  border-radius: var(--radius-pill);
  background: linear-gradient(90deg, rgba(17, 17, 17, 0.035), rgba(17, 17, 17, 0.07), rgba(17, 17, 17, 0.035));
  animation: pulse 1.3s infinite ease-in-out;
}
```

### Fix #6: Empty State Copy (index.tsx ~L249-251)

```tsx
// BEFORE:
<Text className='mini-loading'>
  {entry?.entryKind === 'fragment' ? '派生词，查看主词条' : '未找到释义'}
</Text>

// AFTER:
<View className='mini-empty-state'>
  <Text className='mini-empty-text'>暂未找到稳定释义</Text>
  <Text 
    className='mini-empty-link' 
    onClick={(e) => { e.stopPropagation(); onExpand?.() }}
  >点击查看上下文解释</Text>
</View>
```

对应 SCSS:
```scss
.mini-empty-state {
  padding: 8rpx 0;
  
  .mini-empty-text {
    display: block;
    color: var(--reader-muted);
    font-size: 24rpx;
    line-height: 1.4;
    margin-bottom: 6rpx;
  }
  
  .mini-empty-link {
    display: block;
    color: var(--annotation-context); // 蓝色链接
    font-size: 22rpx;
    line-height: 1.4;
    text-decoration: underline;
    text-decoration-color: rgba(76, 145, 194, 0.4);
  }
}
```

## ✅ 验证清单

修改完成后，请逐项检查：

### Visual Check (目视检查)
- [ ] Sheet 从底部弹出时，阴影是否向上投射？
- [ ] Sheet 弹出动画是否感觉更从容（~280ms）？
- [ ] 来源例句区块是否看起来更紧凑（14rpx圆角）？
- [ ] Tab激活指示器是否更精致（2rpx）？
- [ ] Loading状态是否显示骨架屏而非spinner？
- [ ] Empty状态是否显示友好的"暂未找到"文案？

### Interaction Check (交互测试)
- [ ] Slip出现/消失动画是否流畅（~160ms）？
- [ ] Sheet拖拽关闭是否灵敏（>60px触发）？
- [ ] 保存按钮状态切换是否即时（optimistic UI）？
- [ ] 所有手势（tap outside, swipe down）是否正常工作？

### Code Quality Check (代码质量)
- [ ] 无console.error或warning？
- [ ] TypeScript类型检查通过？
- [ ] SCSS编译无错误？
- [ ] 无硬编码的颜色/尺寸值（全部使用变量）？

## 🎨 最终对比目标

修改后的组件应该能够通过以下测试：

**AI Slop Test**: "如果有人告诉我这是AI做的，我会相信吗？"
→ 应该回答：❌ **不会** - 因为它有明确的文具隐喻、精确的token系统、克制的色彩

**Brief Match Test**: "每个像素都能追溯到Design Brief吗？"
→ 应该回答：✅ **是的** - 408rpx宽度、24rpx圆角、34rpx词头、86vh高度等全部匹配

**User Emotion Test**: "用户在使用时的情感反应是什么？"
→ 应该回答：😌 **平静且高效** - 像翻阅书页脚注一样自然
