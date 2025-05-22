<script setup>
import { RouterView } from 'vue-router'
</script>

<template>
  <RouterView />
</template>

<style>
/* 全局CSS变量 */
:root {
  --primary-color: #1a1a1a; /* 主色-深黑 */
  --primary-light: #2c2c2c;
  --primary-dark: #000000;
  --secondary-color: #f0f0f0;
  --accent-color: #e63946; /* 强调色-红色 */
  --text-color: #333333;
  --text-light: #666666;
  --success-color: #2a9d8f;
  --warning-color: #e9c46a;
  --danger-color: #e63946;
  --white: #ffffff;
  --light-bg: #f0f0f0;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  font-family: 'Arial', sans-serif;
}

body {
  min-height: 100vh;
  background-color: var(--light-bg);
}
</style>

