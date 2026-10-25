-- wireshark_dissector.lua
-- Custom Wireshark Protocol Dissector for our 16-Byte Cross-Layer ABR & XOR FEC Header
-- Usage in Wireshark: Analyze -> Reload Lua Plugins (or run `wireshark -X lua_script:wireshark_dissector.lua output/stream_capture.pcap`)

cross_abr_proto = Proto("CrossLayerABR", "Cross-Layer Delay-Gradient ABR & XOR FEC Protocol")

f_seq       = ProtoField.uint16("crossabr.seq_num",      "Sequence Number", base.DEC)
f_ts        = ProtoField.uint32("crossabr.timestamp_ms", "Timestamp (ms)",  base.DEC)
f_stream    = ProtoField.uint8 ("crossabr.stream_type",  "Stream Type (0=Audio, 1=Video)", base.DEC)
f_tier      = ProtoField.uint8 ("crossabr.bitrate_tier", "Bitrate Tier (0=1080p..3=240p)", base.DEC)
f_ptype     = ProtoField.uint8 ("crossabr.packet_type",  "Packet Type (0=Media, 1=XOR_FEC)", base.DEC)
f_gid       = ProtoField.uint8 ("crossabr.fec_group_id", "FEC Group ID", base.DEC)
f_size      = ProtoField.uint16("crossabr.payload_size", "Payload Size / XOR Length", base.DEC)
f_flags     = ProtoField.uint32("crossabr.flags",        "Cross-Layer Flags (k, idx, stride_D, UEP)", base.HEX)

cross_abr_proto.fields = { f_seq, f_ts, f_stream, f_tier, f_ptype, f_gid, f_size, f_flags }

function cross_abr_proto.dissector(buffer, pinfo, tree)
    if buffer:len() < 16 then return end
    pinfo.cols.protocol = "CROSS-ABR-FEC"
    local subtree = tree:add(cross_abr_proto, buffer(0, 16), "Cross-Layer ABR 16-Byte Transport Header")
    subtree:add(f_seq,    buffer(0, 2))
    subtree:add(f_ts,     buffer(2, 4))
    subtree:add(f_stream, buffer(6, 1))
    subtree:add(f_tier,   buffer(7, 1))
    subtree:add(f_ptype,  buffer(8, 1))
    subtree:add(f_gid,    buffer(9, 1))
    subtree:add(f_size,   buffer(10, 2))
    subtree:add(f_flags,  buffer(12, 4))
end

local udp_port = DissectorTable.get("udp.port")
udp_port:add(19501, cross_abr_proto)
udp_port:add(19502, cross_abr_proto)
