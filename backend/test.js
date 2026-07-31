
function videoPlannerData() {
    return {
        platforms: ['TikTok', 'YouTube', 'Facebook'],
        selectedPlatform: 'TikTok',
        channels: [
            {id: 1, name: 'DAFA Official TikTok', platform: 'TikTok'},
            {id: 2, name: 'DAFA Shorts', platform: 'YouTube'}
        ],
        selectedChannel: 1,
        selectedMonth: 6,
        campaigns: [],
        selectedCampaignId: '',
        showCreateCampaign: false,
        newCampaignName: '',
        newCampaignGoal: '',
        newCampaignChannel: '',
        creatingCamp: false,
        videoCount: 10,
        contentProportions: [],
        plans: [],
        generating: false,
        researching: false,
        researchResult: '',
        renderMarkdown(text) {
            if (!text) return '';
            if (typeof marked !== 'undefined') {
                return marked.parse(text);
            }
            return text.replace(/\n/g, '<br>');
        },
        addProportion() {
            this.contentProportions.push({ name: '', percentage: 0 });
        },
        removeProportion(index) {
            this.contentProportions.splice(index, 1);
        },
        get filteredChannels() {
            return this.channels.filter(c => c.platform.toLowerCase() === this.selectedPlatform.toLowerCase());
        },
        get filteredCampaigns() {
            if(!this.selectedChannel) return this.campaigns;
            return this.campaigns.filter(c => !c.channel_id || c.channel_id == this.selectedChannel);
        },
        get selectedChannelPlans() {
            return this.plans;
        },
        init() {
            this.$watch('selectedPlatform', () => {
                let fc = this.filteredChannels;
                if(fc.length > 0) this.selectedChannel = fc[0].id;
                else this.selectedChannel = null;
            });
            this.$watch('selectedCampaignId', () => {
                this.loadPlans();
                let camp = this.campaigns.find(c => c.id == this.selectedCampaignId);
                if(camp) {
                    if (camp.channel_id) {
                        this.selectedChannel = camp.channel_id;
                        let chan = this.channels.find(c => c.id == camp.channel_id);
                        if(chan) this.selectedPlatform = chan.platform;
                    }
                    if (camp.research_data) {
                        this.researchResult = camp.research_data;
                    } else {
                        this.researchResult = '';
                    }
                } else {
                    this.researchResult = '';
                }
            });
            this.loadChannels();
            this.loadCampaigns();
        },
        async loadCampaigns() {
            try {
                const res = await fetch('/api/v1/campaigns/?type=Video', {
                    headers: { "Authorization": "Bearer " + localStorage.getItem("token") }
                });
                if (res.ok) {
                    this.campaigns = await res.json();
                }
            } catch (err) {
                console.error(err);
            }
        },
        async createCampaign() {
            if(!this.newCampaignName || !this.newCampaignGoal) {
                window.showToast?.('Vui lòng nhập tên và mục tiêu chiến dịch', 'warning');
                return;
            }
            this.creatingCamp = true;
            try {
                const mm = String(this.selectedMonth || 6).padStart(2, '0');
                const yyyy = new Date().getFullYear();
                const res = await fetch('/api/v1/campaigns/', {
                    method: 'POST',
                    headers: { 
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + localStorage.getItem("token") 
                    },
                    body: JSON.stringify({
                        name: this.newCampaignName,
                        month_year: `${mm}-${yyyy}`,
                        core_theme: this.newCampaignGoal,
                        campaign_type: 'Video',
                        web_frequency: 0,
                        fanpage_frequency: 0,
                        channel_id: this.newCampaignChannel ? parseInt(this.newCampaignChannel) : null
                    })
                });
                if (res.ok) {
                    const camp = await res.json();
                    window.showToast?.('Tạo chiến dịch thành công', 'success');
                    await this.loadCampaigns();
                    this.selectedCampaignId = camp.id;
                    this.showCreateCampaign = false;
                    this.newCampaignName = '';
                    this.newCampaignGoal = '';
                } else {
                    window.showToast?.('Lỗi tạo chiến dịch', 'error');
                }
            } catch(e) {
                console.error(e);
            } finally {
                this.creatingCamp = false;
            }
        },
        async loadPlans() {
            if(!this.selectedCampaignId) {
                this.plans = [];
                return;
            }
            try {
                const res = await fetch('/api/v1/video-plans/campaign/' + this.selectedCampaignId + '/plans', {
                    headers: { "Authorization": "Bearer " + localStorage.getItem("token") }
                });
                if(res.ok) {
                    this.plans = await res.json();
                }
            } catch(e) { console.error(e); }
        },
        async loadChannels() {
            try {
                const res = await fetch('/api/v1/video-channels/', {
                    headers: { "Authorization": "Bearer " + localStorage.getItem("token") }
                });
                if (res.ok) {
                    this.channels = await res.json();
                    let fc = this.filteredChannels;
                    if(fc.length > 0) this.selectedChannel = fc[0].id;
                }
            } catch (err) {
                console.error(err);
            }
        },
        getChannelName(id) {
            let c = this.channels.find(c => c.id == id);
            return c ? c.name : 'Unknown Channel';
        },
        async runResearch() {
            if(!this.selectedCampaignId) {
                window.showToast?.('Vui lòng chọn hoặc tạo chiến dịch trước!', 'warning');
                return;
            }
            this.researching = true;
            this.researchResult = '';
            window.showToast?.('🤖 Đang tiến hành phân tích thị trường (có thể mất 30s)...', 'info');
            
            try {
                const res = await fetch(`/api/v1/campaigns/${this.selectedCampaignId}/research`, {
                    method: 'POST',
                    headers: { "Authorization": "Bearer " + localStorage.getItem("token") }
                });
                if (res.ok) {
                    const camp = await res.json();
                    this.researchResult = camp.research_data;
                    window.showToast?.('Nghiên cứu thành công!', 'success');
                    // Cập nhật lại dữ liệu trong campaigns list
                    const idx = this.campaigns.findIndex(c => c.id == camp.id);
                    if(idx !== -1) this.campaigns[idx].research_data = camp.research_data;
                } else {
                    window.showToast?.('Lỗi phân tích thị trường', 'error');
                }
            } catch (err) {
                console.error(err);
                window.showToast?.('Lỗi phân tích thị trường', 'error');
            } finally {
                this.researching = false;
            }
        },
        async generatePlan() {
            if(!this.selectedCampaignId) {
                window.showToast?.('Vui lòng chọn chiến dịch!', 'warning');
                return;
            }
            if(!this.selectedChannel && this.channels.length > 0) {
                this.selectedChannel = this.channels[0].id;
            } else if (!this.selectedChannel) {
                window.showToast?.('Vui lòng tạo kênh trước khi lập kế hoạch!', 'warning');
                return;
            }
            
            const payload = {
                campaign_id: parseInt(this.selectedCampaignId),
                month_year: "2026-" + String(this.selectedMonth || 6).padStart(2, '0'),
                objective: this.campaignGoal || "Lên kế hoạch video chi tiết",
                total_posts: parseInt(this.videoCount || 0) || 10,
                channel_id: parseInt(this.selectedChannel || 0) || null,
                content_proportions: this.contentProportions.map(p => ({
                    name: p.name,
                    percentage: parseInt(p.percentage || 0) || 0
                }))
            };
            
            this.generating = true;
            window.showToast?.('Đang kết nối AI... Vui lòng đợi trong giây lát!', 'info');

            try {
                const res = await fetch('/api/v1/video-plans/generate', {
                    method: 'POST',
                    headers: { 
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + localStorage.getItem("token")
                    },
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    this.plans = await res.json();
                    window.showToast?.('Tạo kế hoạch thành công!', 'success');
                } else {
                    window.showToast?.('Lỗi tạo kế hoạch', 'error');
                }
            } catch (err) {
                console.error(err);
                window.showToast?.('Lỗi tạo kế hoạch', 'error');
            } finally {
                this.generating = false;
            }
        },
        async approvePlan() {
            if(!this.selectedCampaignId) return;
            if(!confirm('Bạn có chắc chắn duyệt toàn bộ kế hoạch này? AI sẽ tự động sinh Kịch bản chi tiết cho từng video.')) return;
            
            this.generating = true;
            window.showToast?.('🤖 AI đang viết kịch bản chi tiết cho từng video...', 'info');
            
            try {
                const res = await fetch(`/api/v1/video-plans/approve-all?campaign_id=${this.selectedCampaignId}`, {
                    method: 'POST',
                    headers: { "Authorization": "Bearer " + localStorage.getItem("token") }
                });
                if(res.ok) {
                    window.showToast?.('Đã duyệt kế hoạch và sinh kịch bản thành công!', 'success');
                    this.loadPlans();
                } else {
                    window.showToast?.('Lỗi duyệt kế hoạch', 'error');
                }
            } catch(e) {
                console.error(e);
            } finally {
                this.generating = false;
            }
        },
        async approveSinglePlan(plan) {
            this.generating = true;
            window.showToast?.('🤖 AI đang viết kịch bản chi tiết...', 'info');
            try {
                const res = await fetch(`/api/v1/video-plans/${plan.id}/approve`, {
                    method: 'POST',
                    headers: { "Authorization": "Bearer " + localStorage.getItem("token") }
                });
                if(res.ok) {
                    window.showToast?.('Đã duyệt kế hoạch và sinh kịch bản thành công!', 'success');
                    window.location.href = '/video-script';
                } else {
                    window.showToast?.('Lỗi duyệt kế hoạch', 'error');
                }
            } catch(e) { console.error(e); }
            finally { this.generating = false; }
        },
        async updatePlan(plan) {
            try {
                const res = await fetch(`/api/v1/video-plans/${plan.id}`, {
                    method: 'PUT',
                    headers: { 
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + localStorage.getItem("token") 
                    },
                    body: JSON.stringify({ 
                        title: plan.title,
                        content_line: plan.content_line,
                        optimal_post_time: plan.optimal_post_time,
                        ai_prompt: plan.ai_prompt
                    })
                });
                if(res.ok) {
                    window.showToast?.('Đã lưu thay đổi', 'success');
                } else {
                    window.showToast?.('Lỗi cập nhật', 'error');
                }
            } catch(e) { console.error(e); }
        },
        async deletePlan(planId) {
            if(!confirm('Xóa kế hoạch này?')) return;
            try {
                const res = await fetch(`/api/v1/video-plans/${planId}`, {
                    method: 'DELETE',
                    headers: { "Authorization": "Bearer " + localStorage.getItem("token") }
                });
                if(res.ok) {
                    window.showToast?.('Đã xóa', 'success');
                    this.loadPlans();
                } else {
                    window.showToast?.('Lỗi xóa', 'error');
                }
            } catch(e) { console.error(e); }
        },
        async deleteCampaign() {
            if(!this.selectedCampaignId) return;
            if(!confirm('Xóa chiến dịch này và TOÀN BỘ kế hoạch bên trong? Không thể hoàn tác!')) return;
            try {
                const res = await fetch(`/api/v1/campaigns/${this.selectedCampaignId}`, {
                    method: 'DELETE',
                    headers: { "Authorization": "Bearer " + localStorage.getItem("token") }
                });
                if(res.ok) {
                    window.showToast?.('Đã xóa chiến dịch', 'success');
                    this.selectedCampaignId = '';
                    await this.loadCampaigns();
                } else {
                    window.showToast?.('Lỗi xóa chiến dịch', 'error');
                }
            } catch(e) { console.error(e); }
        }
    }
}
