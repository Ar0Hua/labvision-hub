<template>
    <div id="basicLayout">
        <a-layout style="min-height: 100vh">
            <a-layout-header class="header">
                <GlobalHeader />
            </a-layout-header>
            <a-layout>
                <GlobalSider class="sider" />
                <a-layout-content class="content">
                    <router-view />
                </a-layout-content>
            </a-layout>
        </a-layout>
    </div>
</template>

<script setup lang="ts">
import GlobalHeader from '@/components/GlobalHeader.vue';
import GlobalSider from '@/components/GlobalSider.vue';
</script>

<style scoped>
#basicLayout .header {
    background-color: #f5f5f5;
    color: unset;
    margin-bottom: 1px;
    padding-inline: 0;
}

#basicLayout .sider {
    background: #fff;
    border-right: 0.5px solid #eee;
    padding-top: 20px;
}

#basicLayout :deep(.ant-menu-root) {
    border-bottom: none !important;
    border-inline-end: none !important;
}

#basicLayout .content {
    padding: 28px;
    background-color: linear-gradient(to right, #fefefe, #fff);
}
</style>
