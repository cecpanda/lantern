# Lantern 后端



## 注意事项

必须承认后端的有些功能失控了，经验不够丰富啊！

- 用户必须有组
- 原则上，用户的组可以为空，但会造成停机单的开单工程为空。
- 开单工程为空的话，会造成订单查询主界面崩溃。
- 如果使用 template scope 解决开单工程为空的情况，但将失去开单工程的表头过滤功能。


## License

[MIT](http://opensource.org/licenses/MIT)

Copyright (c) 2018-present, doocan