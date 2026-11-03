mod kit;
use kit::*;
use nfsu2_roam::RoamOptions;

#[test]
fn all_49_players_share_links_despite_old_rooms_crews_blocks_and_low_limits() {
    let mut k = Kit::new(RoamOptions {
        shared_session: true, degree: 48, min_degree: 48, max_players: 49,
        ..Default::default()
    });
    for i in 0..49u32 {
        let vip = 0x0a4d0002 + i;
        k.from(vip, &hello_with(100 + i, &HelloOpts {
            core: 10, links: 1, room: i + 1, crews: Some(&[i + 1000]), name: b"player",
            ..Default::default()
        }));
        k.from(vip, &snap(100 + i, [i as f64 * 200.0, 0.0, 0.0]));
        k.hub.blocks(vip, vec!["player".into()]);
    }
    k.hub.tick();
    let lists = k.lists();
    for i in 0..49u32 {
        assert_eq!(lists.get(&format!("{}:47210", 0x0a4d0002 + i)).unwrap().len(), 48);
    }
    assert_eq!(k.hub.in_roam(), 49);
    assert!(k.hub.in_rooms().is_empty());
    assert_eq!(k.hub.in_crews(&[1000]), vec![0]);
}
