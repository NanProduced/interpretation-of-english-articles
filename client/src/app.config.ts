export default {
  pages: [
    'pages/home/index',
    'pages/input/index',
    'pages/result/index',
  ],
  subPackages: [
    {
      root: 'packageA',
      pages: [
        'history/index',
        'vocab/index',
        'profile/index',
        'credit-detail/index',
      ],
    },
    {
      root: 'packageB',
      pages: [
        'daily-reader/index',
        'daily-reader-archive/index',
      ],
    },
    {
      root: 'packageC',
      pages: [
        'feedback/index',
        'feedback/my-feedback',
        'onboarding/index',
      ],
    },
  ],
  window: {
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#fff',
    navigationBarTitleText: 'Claread透读',
    navigationBarTextStyle: 'black',
  },
}
